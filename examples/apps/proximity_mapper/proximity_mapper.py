#!/usr/bin/env python3

# Copyright (c) 2018 Anki, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Maps a region around Vector using the proximity sensor.

Vector will turn in place and use his sensor to detect walls in his
local environment.  These walls are displayed in a 3d viewer.  The
visualizer does not effect the robot's internal state or behavior.

Vector expects this environment to be static - if objects are moved
he will have no knowledge of them.
"""

import asyncio
import concurrent
from math import cos, sin, inf, acos
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
from proximity_mapper_state import ClearedTerritory, MapState, Wall, WallSegment   # pylint: disable=wrong-import-position
from opengl_viewer import OpenGLViewer   # pylint: disable=wrong-import-position

import anki_vector   # pylint: disable=wrong-import-position
from anki_vector.util import parse_command_args, radians, degrees, distance_mm, speed_mmps, Vector3  # pylint: disable=wrong-import-position

# Constants

#: The maximum distance (in millimeters) the scan considers valid for a proximity respons.
#: Wall detection past this threshold will be disregarded, and an 'open' node will
#: be created at this distance instead.  Increasing this value may degrade the
#: reliability of this program, see note below:
#:
#: NOTE: The proximity sensor works by sending a light pulse, and seeing how long that pulse takes
#: to reflect and return to the sensor.  The proximity sensor does not specifically have a maximum
#: range, but will get unreliable results below a certain return signal strength.  This return signal
#: is impacted by environmental conditions (such as the orientation and material of the detected obstacle)
#: as well as the distance.  Additionally, increasing this radius will reduce the resolution of contact
#: points, necessitating changes to PROXIMITY_SCAN_SAMPLE_FREQUENCY_HZ and PROXIMITY_SCAN_BIND_THRESHOLD_MM
#: to maintain effective wall prediction.
PROXIMITY_SCAN_DISTANCE_THRESHOLD_MM = 300

#: The distance (in millimeters) to place an open node if no proximity results are detected along
#: a given line of sight.  This should be smaller than the distance threshold, since these nodes
#: indicate safe points for the robot to drive to, and the robot's size should be taken into account
#: when estimating a maximum safe driving distance
PROXIMITY_SCAN_OPEN_NODE_DISTANCE_MM = 230

#: How frequently (in hertz) the robot checks proximity data while doing a scan.
PROXIMITY_SCAN_SAMPLE_FREQUENCY_HZ = 15.0

#: How long (in seconds) the robot spends doing it's 360 degree scan.
PROXIMITY_SCAN_TURN_DURATION_S = 10.0

#: How close (in millimeters) together two detected contact points need to be for the robot to
#: consider them part of a continuous wall.
PROXIMITY_SCAN_BIND_THRESHOLD_MM = 30.0

#: A delay (in seconds) the program waits after the scan finishes before shutting down.
#: This allows the user time to explore the mapped 3d environment in the viewer and can be
#: Tuned to any desired length.  A value of 0.0 will prevent the viewer from closing.
PROXIMITY_EXPLORATION_SHUTDOWN_DELAY_S = 8.0


# @TODO: once pathfinding is more reliable, this should be enabled.
#: ACTIVELY_EXPLORE_SPACE can be activated to allow the robot to move
#: into an open space after scanning, and continue the process until all open
#: spaces are explored.
ACTIVELY_EXPLORE_SPACE = True
#: The speed (in millimeters/second) the robot drives while exploring.
EXPLORE_DRIVE_SPEED_MMPS = 40.0
#: The speed (in degrees/second) the robot turns while exploring.
EXPLORE_TURN_SPEED_DPS = 90.0


#: Takes a position in 3d space where a collection was detected, and adds it to the map state
#: by either creating a wall, adding to wall or storing a loose contact point.
async def add_proximity_contact_to_state(node_position: Vector3, state: MapState):

    # Comparison function for sorting points by distance.
    def compare_distance(elem):
        return (elem - node_position).magnitude_squared

    # Comparison function for sorting walls by distance using their head as a reference point.
    def compare_head_distance(elem):
        return (elem.vertices[0] - node_position).magnitude_squared

    # Comparison function for sorting walls by distance using their tail as a reference point.
    def compare_tail_distance(elem):
        return (elem.vertices[-1] - node_position).magnitude_squared

    # Sort all the loose contact nodes not yet incorporated into walls by
    # their distance to our reading position.  If the nearest one is within
    # our binding threshold - store it as a viable wall creation partner.
    # (infinity is used as a standin for 'nothing')
    closest_contact_distance = inf
    if state.contact_nodes:
        state.contact_nodes.sort(key=compare_distance)
        closest_contact_distance = (state.contact_nodes[0] - node_position).magnitude
        if closest_contact_distance > PROXIMITY_SCAN_BIND_THRESHOLD_MM:
            closest_contact_distance = inf

    # Sort all the walls both by head and tail distance from our sample
    # if either of the results are within our binding threshold, store them
    # as potential wall extension candidates for our sample.
    # (infinity is used as a standin for 'nothing')
    closest_head_distance = inf
    closest_tail_distance = inf
    if state.walls:
        state.walls.sort(key=compare_tail_distance)
        closest_tail_distance = (state.walls[0].vertices[-1] - node_position).magnitude
        if closest_tail_distance > PROXIMITY_SCAN_BIND_THRESHOLD_MM:
            closest_tail_distance = inf

        state.walls.sort(key=compare_head_distance)
        closest_head_distance = (state.walls[0].vertices[0] - node_position).magnitude
        if closest_head_distance > PROXIMITY_SCAN_BIND_THRESHOLD_MM:
            closest_head_distance = inf

    # Create a new wall if a loose contact node is in bind range and
    # is closer than any existing wall.  The contact node will be removed.
    if closest_contact_distance <= PROXIMITY_SCAN_BIND_THRESHOLD_MM and closest_contact_distance < closest_head_distance and closest_contact_distance < closest_tail_distance:
        state.walls.append(Wall(WallSegment(state.contact_nodes[0], node_position)))
        state.contact_nodes.pop(0)

    # Extend a wall if it's head is within bind range and is closer than
    # any loose contacts or wall tails.
    elif closest_head_distance <= PROXIMITY_SCAN_BIND_THRESHOLD_MM and closest_head_distance < closest_contact_distance and closest_head_distance < closest_tail_distance:
        state.walls[0].insert_head(node_position)

    # Extend a wall if it's tail is within bind range and is closer than
    # any loose contacts or wall heads.
    elif closest_tail_distance <= PROXIMITY_SCAN_BIND_THRESHOLD_MM and closest_tail_distance < closest_contact_distance and closest_tail_distance < closest_head_distance:
        state.walls.sort(key=compare_tail_distance)
        state.walls[0].insert_tail(node_position)

    # If nothing was found to bind with, store the sample as a loose contact node.
    else:
        state.contact_nodes.append(node_position)


#: Takes a position in 3d space and adds it to the map state as an open node
async def add_proximity_non_contact_to_state(node_position: Vector3, state: MapState):
    # Check to see if the uncontacted sample is inside of any area considered already explored.
    is_open_unexplored = True
    for ct in state.cleared_territories:
        if (node_position - ct.center).magnitude < ct.radius:
            is_open_unexplored = False

    # If the uncontacted sample is in unfamiliar ground, store it as an open node.
    if is_open_unexplored:
        state.open_nodes.append(node_position)


#: Modifies the map state with the details of a proximity reading
async def analyze_proximity_sample(reading: anki_vector.proximity.ProximitySensorData, robot: anki_vector.robot.Robot, state: MapState):
    # Check if the reading meets the engine's metrics for valid, and that its within our specified distance threshold.
    reading_contacted = reading.is_valid and reading.distance.distance_mm < PROXIMITY_SCAN_DISTANCE_THRESHOLD_MM

    if reading_contacted:
        # The distance will either be the reading data, or our threshold distance if the reading is considered uncontacted.
        reading_distance = reading.distance.distance_mm if reading_contacted else PROXIMITY_SCAN_DISTANCE_THRESHOLD_MM

        # Convert the distance to a 3d position in worldspace.
        reading_position = Vector3(
            robot.pose.position.x + cos(robot.pose_angle_rad) * reading_distance,
            robot.pose.position.y + sin(robot.pose_angle_rad) * reading_distance,
            robot.pose.position.z)

        await add_proximity_contact_to_state(reading_position, state)
    else:
        # Convert the distance to a 3d position in worldspace.
        safe_driving_position = Vector3(
            robot.pose.position.x + cos(robot.pose_angle_rad) * PROXIMITY_SCAN_OPEN_NODE_DISTANCE_MM,
            robot.pose.position.y + sin(robot.pose_angle_rad) * PROXIMITY_SCAN_OPEN_NODE_DISTANCE_MM,
            robot.pose.position.z)

        await add_proximity_non_contact_to_state(safe_driving_position, state)


#: repeatedly collects proximity data sample and converts them to nodes and walls for the map state
async def collect_proximity_data_loop(robot: anki_vector.robot.Robot, future: concurrent.futures.Future, state: MapState):
    try:
        scan_interval = 1.0 / PROXIMITY_SCAN_SAMPLE_FREQUENCY_HZ

        # Runs until the collection_active flag is cleared.
        # This flag is cleared external to this function.
        while state.collection_active:
            # Collect proximity data from the sensor.
            reading = robot.proximity.last_sensor_reading
            if reading is not None:
                await analyze_proximity_sample(reading, robot, state)
            await asyncio.sleep(scan_interval)

    # Exceptions raised in this process are ignored, unless we set them on the future, and then run future.result() at a later time
    except Exception as e:    # pylint: disable=broad-except
        future.set_exception(e)
    finally:
        future.set_result(state)


#: Updates the map state by rotating 360 degrees and collecting/applying proximity data samples.
async def scan_area(robot: anki_vector.robot.Robot, state: MapState):
    collect_future = concurrent.futures.Future()

    # The collect_proximity_data task relies on this external trigger to know when its finished.
    state.collection_active = True

    # Turn around in place.
    turn_call = robot.behavior.turn_in_place(angle=degrees(360.0), speed=degrees(360.0 / PROXIMITY_SCAN_TURN_DURATION_S))
    # Activate the collection task while the robot turns in place.
    collect_task = robot.loop.create_task(collect_proximity_data_loop(robot, collect_future, state))

    # Wait for the turning to finish, then send the signal to kill the collection task.
    await turn_call
    state.collection_active = False

    # Wait for the collection task to finish.
    await collect_task
    # While the result of the task is not used, this call will propagate any exceptions that
    # occured in the task, allowing for debug visibility.
    collect_future.result()


#: Top level call to perform exploration and environment mapping
async def map_explorer(robot: anki_vector.robot.Robot, viewer: OpenGLViewer):
    # Drop the lift, so that it does not block the proximity sensor
    await robot.behavior.set_lift_height(30.0)

    # Create the map state, and add it's rendering function to the viewer's render pipeline
    state = MapState()
    viewer.add_render_call(state.render)

    # Comparison function used for sorting which open nodes are the furthest from all existing
    # walls and loose contacts.
    # (Using 1/r^2 to respond strongly to small numbers of close contact and weaking to many distant contacts)
    def open_point_sort_func(position: Vector3):
        proximity_sum = 0
        for p in state.contact_nodes:
            proximity_sum = proximity_sum + 1 / (p - position).magnitude_squared
        for c in state.walls:
            for p in c.vertices:
                proximity_sum = proximity_sum + 1 / (p - position).magnitude_squared
        return proximity_sum

    # Loop until running out of open samples to navigate to,
    # or if the process has yet to start (indicated by a lack of cleared_territories).
    while (state.open_nodes and ACTIVELY_EXPLORE_SPACE) or not state.cleared_territories:
        # Delete any open samples range of the robot.
        state.open_nodes = [position for position in state.open_nodes if (position - robot.pose.position).magnitude > PROXIMITY_SCAN_DISTANCE_THRESHOLD_MM]

        # Collect map data for the robot's current location.
        await scan_area(robot, state)

        # Add where the robot is to the map's cleared territories.
        state.cleared_territories.append(ClearedTerritory(robot.pose.position, PROXIMITY_SCAN_DISTANCE_THRESHOLD_MM))

        # @TODO: This is currently unreliable.  This whole block should ideally be replaced with the go_to_pose actions when
        # that action's reliability is improved.  Alternatively, the turn&drive commands can be modified to respond to collisions
        # by cancelling rather than hanging indefinitely.  After either change, ACTIVELY_EXPLORE_SPACE should be defaulted True
        if ACTIVELY_EXPLORE_SPACE and state.open_nodes:
            # Sort the open nodes and find our next navigation point.
            state.open_nodes.sort(key=open_point_sort_func)
            nav_point = state.open_nodes[0]

            # Calculate the distance and direction of this next navigation point.
            nav_point_delta = Vector3(
                nav_point.x - robot.pose.position.x,
                nav_point.y - robot.pose.position.y,
                0)
            nav_distance = nav_point_delta.magnitude
            nav_direction = nav_point_delta.normalized

            # Convert the nav_direction into a turn angle relative to the robot's current facing.
            robot_forward = Vector3(*robot.pose.rotation.to_matrix().forward_xyz).normalized
            turn_angle = acos(nav_direction.dot(robot_forward))
            if nav_direction.cross(robot_forward).z > 0:
                turn_angle = -turn_angle

            # Turn toward the nav point, and drive to it.
            await robot.behavior.turn_in_place(angle=radians(turn_angle), speed=degrees(EXPLORE_TURN_SPEED_DPS))
            try:
                # if more than 125% of the expected drive time elapses without the drive_straight concluding, it
                # likely means the robot encountered a cliff or obstacle.
                expected_drive_time = nav_distance / EXPLORE_DRIVE_SPEED_MMPS
                await asyncio.wait_for(robot.behavior.drive_straight(distance=distance_mm(nav_distance), speed=speed_mmps(EXPLORE_DRIVE_SPEED_MMPS)),
                                       1.25 * expected_drive_time,
                                       loop=robot.loop)
            except asyncio.TimeoutError:
                print('obstacle encountered while moving, continuing exploration from current position')

    if PROXIMITY_EXPLORATION_SHUTDOWN_DELAY_S == 0.0:
        while True:
            await asyncio.sleep(1.0)
    else:
        print('finished exploring - waiting an additional {0} seconds, then shutting down'.format(PROXIMITY_EXPLORATION_SHUTDOWN_DELAY_S))
        await asyncio.sleep(PROXIMITY_EXPLORATION_SHUTDOWN_DELAY_S)


# Connect to the robot
args = parse_command_args()
with anki_vector.Robot(args.serial, show_viewer=True) as robotInstance:
    # Creates a 3d viewer for the connected robot.
    viewerInstance = OpenGLViewer(robot=robotInstance)

    # The opengl 3d viewer has to run on the main thread, so control is given to
    # it via the blocking 'run' call.  The core loop of our program is injected into
    # this call to run in parallel on a secondary thread.  When the injected function
    # finishes, the viewer will automatically shut down and relinquish control of the
    # main thread.
    viewerInstance.run(map_explorer)
