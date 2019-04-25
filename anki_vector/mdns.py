# Copyright (c) 2019 Anki, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This contains the :class:`VectorMdns` class for discovering Vector (without already knowing
the IP address) on a LAN (Local Area Network) over mDNS.

mDNS (multicast DNS) is a protocol for sending UDP packets containing a DNS query to all
devices on your Local Area Network. If a device knows how to answer the DNS query, it
will respond by multicasting a UDP packet containing the relevant DNS records.
"""
from threading import Condition
import sys


class VectorMdns:  # pylint: disable=too-few-public-methods
    """`VectorMdns` provides a static method for discovering a Vector on the same LAN as
    the SDK program and retrieving its IP address.
    """

    @staticmethod
    def find_vector(name: str, timeout=5):
        """
        :param name: A name like `"Vector-A1B2"`. If :code:`None`, will search for any Vector.
        :param timeout: The discovery will timeout in :code:`timeout` seconds. Default value is :code:`5`.
        :returns: **dict** or **None** -- if Vector found, **dict** contains keys `"name"` and `"ipv4"`

        .. testcode::

            import anki_vector
            vector_mdns = anki_vector.mdns.VectorMdns.find_vector("Vector-A1B2")

            if vector_mdns is not None:
              print(vector_mdns['ipv4'])
            else:
              print("No Vector found on your local network!")
        """

        # synchronously search for Vector for up to 5 seconds
        vector_name = name  # should be like 'Vector-V3C7'
        return VectorMdns._start_mdns_listener(vector_name, timeout)

    @staticmethod
    def _start_mdns_listener(name, timeout):
        try:
            from zeroconf import ServiceBrowser, Zeroconf
        except ImportError:
            sys.exit("Cannot import from Zeroconf: Do `pip3 install --user zeroconf` to install")

        # create a Condition object and acquire the underlying lock
        cond = Condition()
        cond.acquire()

        # instantiate zeroconf and our MdnsListner object for listening to events
        zeroconf = Zeroconf()
        vector_fullname = None

        if name is not None:
            vector_fullname = name + ".local."

        listener = _MdnsListener(vector_fullname, cond)

        # browse for the _ankivector TCP MDNS service, sending events to our listener
        ServiceBrowser(zeroconf, "_ankivector._tcp.local.", listener)

        # block until 'timeout' seconds or until we discover vector
        cond.wait(timeout)

        # close zeroconf
        zeroconf.close()

        # return an IPv4 string (or None)
        if listener.ipv4 is None:
            return None

        return {'ipv4': listener.ipv4, 'name': listener.name}


class _MdnsListener:
    """_MdnsListener is an internal helper class which listens for mDNS messages.

    :param name_filter: A String to filter the mDNS responses by name (e.g., `"Vector-A1B2"`).
    :param condition: A Condition object to be used for signaling to caller when robot has been discovered.
    """

    def __init__(self, name_filter: str, condition):
        self.name_filter = name_filter
        self.cond = condition
        self.ipv4 = None
        self.name = ""

    @staticmethod
    def _bytes_to_str_ipv4(ip_bytes):
        return str(ip_bytes[0]) + "." +  \
            str(ip_bytes[1]) + "." +  \
            str(ip_bytes[2]) + "." +  \
            str(ip_bytes[3])

    def remove_service(self, zeroconf, mdns_type, name):
        # detect service removal
        pass

    def add_service(self, zeroconf, mdns_type, name):
        # detect service
        info = zeroconf.get_service_info(mdns_type, name)

        if (self.name_filter is None) or (info.server.lower() == self.name_filter.lower()):
            # found a match for our filter or there is no filter
            self.cond.acquire()
            self.ipv4 = _MdnsListener._bytes_to_str_ipv4(info.address)   # info.address is IPv4 (DNS record type 'A')
            self.name = info.server

            # cause anything waiting for this condition to end waiting
            # and release so the other thread can continue
            self.cond.notify()
            self.cond.release()
