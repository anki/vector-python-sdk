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

"""
Protobuf and gRPC messages exposed to the Vector Python SDK.

.. warning::

    This package is provided to understand the messages passed between the SDK and Vector,
    and it should not be necessary for writing code that uses the SDK.

.. code-block::
    python

    from anki_vector.messaging import client, protocol

    async def send_version_request(interface: client.ExternalInterfaceStub, client_version, min_host_version):
        \"\"\"This function needs to be executed and awaited in the same event loop
        as the interface is created.
        \"\"\"
        # Create a protocol version request message
        version = protocol.ProtocolVersionRequest(client_version=client_version,
                                                  min_host_version=min_host_version)

        # Send the protocol version to the external interface and await the result
        protocol_version = await interface.ProtocolVersion(version)

For information about individual messages and their parameters, see :doc:`the protobuf documentation </proto>`.
"""

from . import protocol
from . import client

__all__ = ['protocol', 'client']
