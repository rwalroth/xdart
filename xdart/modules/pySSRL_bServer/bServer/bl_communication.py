import socket
import time
import types
import sys
import yaml
import copy
import logging
from logging import info, warning, critical, debug
import asyncio

sys.path.append('C:\\Users\\Public\\repos\\xdart')
from xdart.modules.pySSRL_bServer.bServer.BL_Error import *
from xdart.modules.pySSRL_bServer.bServer.useful_func import *

class BL_Communication():
    """Different communication protocals can be added and extended through this class. A few base functions like writeCommand and readResponse should not depend on the communication protocal and will be implemented here."""
    async def writeCommand(self, mCmd, terminator=None):
        """ Encode the string and add the appropiate send terminator to the command.
        """
        debug("writeCommand: '{}'".format(mCmd))
        if terminator is None:
            mCmd += self.SEND_TERMINATOR

        encCmd = mCmd.encode(self.STR_ENCODING)


        await self.write(encCmd)
        debug("writeCommand: finished writing command")

    async def readResponse(self, terminator=None, listSeparator=None):
        """Read the response from the beamline, strip the terminators, and break the response into a list seperated by 'listSeparator'.
        """

        if terminator is None:
            terminator = self.RECEIVE_TERMINATOR

        if listSeparator is None:
            listSeparator = self.RECEIVE_TERMINATOR

        try:
            #print("Before read")
            bytesReceived = await (self.read(terminator))

            print("after read: '{}'".format(bytesReceived))

        except self.CommandError:
            warning("got command error in read")
            raise
        except:
            warning("Unexpected error in read:", sys.exc_info()[0])
            raise

        returnedText = bytesReceived.decode(self.STR_ENCODING)

        strippedText = returnedText.rstrip(terminator)
        parsedList = strippedText.split(listSeparator)

        filteredList = list(filter(None, parsedList)) #Remove the empty items from the list
        return filteredList

    
    #### These functions should be overloaded by the subclass for each communication protocol
    #def read(self, terminator=None):
    #    pass

    #def write(self, toSend):
    #    pass
       
    #def __init__(self, mi):
    #    pass


class tmp_bi():
    """TEMP class to let me assign a few things the BL_Interaction class will handle later."""
    def __init__(self, loop, beamline_name):
        self.loop = loop
        self.beamline_name = beamline_name
    
    
class BL_SPEC(BL_Communication):
    """Functions for communicating with SPEC beamlines through TCPIP sockets. This is the fairly low level stuff.
    One could imagine writing similar classes for ICS """
    def __init__(self, bi):
        """Set the IP address and port for the beamline by loading from the config file. Configure buffer sizes, encodings, and terminators. Call connect. Note: 'mi' is the motor interactor that will hold this object."""

        #Record a reference to the motor interactor that holds this object
        self.bi = bi

        #Init dict for asyncio socket
        self.s = {'reader': None, 'writer': None}

        #Initialize communication paramters that don't belong in the buffer
        self.BUFFER_SIZE = 1024*1024
        self.TIMEOUT = 1 #This is in seconds
        self.STR_ENCODING = 'ascii'
        self.SEND_TERMINATOR = "\n"
        self.RECEIVE_TERMINATOR = "\n"
        self.MAX_READ_TIME = 5
        #Load up the config file for this beamline
#        self.load_beamline_config(self.bi.beamline_name)

        #This is a bit crude. Lets set the config filename/path here.
        self.beamline_config_filename = './config/beamline_catalogue.yml'

        parsed_config = load_yaml_config(self.beamline_config_filename)
        try:

            #Take the elements in the config and add them to the object
            bl_config = parsed_config[self.bi.beamline_name]

            for (key, val) in bl_config.items():
                print("adding '{}' -> '{}'".format(key, val))
                setattr(self, key, val)
        except:
            print('BL_SPEC: init: hit an error: {}', sys.exc_info()[0])
            raise


        #Get the async components setup
        asyncio.ensure_future(self.setup(), loop=self.bi.loop)

    async def setup(self):
        # Parse the config file and add all of the relevent attributes to the LMD_TCPIP object
        debug("setup: doing async components of beamline setup")
        # Connect to the motor
        try:
            await self.connect()
        except:
            raise RuntimeError("setup: problem in setup of {}".format(self.bi.beamline_name))
        else:
            print("motor '{}' setup successful. socket object = {}".format(self.bi.beamline_name, self.s))


    async def reconnect(self):
        """CLose and then open the socket again"""
        try:
            self.close()
            await self.connect()
        except SPECcommunicationError:
            debug("reconnect(): Problem communicating w/ SPEC during reconnect")
        except:
            debug("reconnect(): Some other exception")
            raise
        else:
            info("reconnect(): reconnected!")
            print("Reconnect worked!")


    async def connect(self):
        """Open the socket and connect to the motor"""
        tcpip = self.TCP_IP
        tcpport = self.TCP_PORT

        info("connecting to {}:{}".format(tcpip, tcpport))
        self.connected = False
        
        try:
            self.s['reader'], self.s['writer'] = await asyncio.wait_for(asyncio.open_connection(host=tcpip, port=tcpport, loop=self.bi.loop), timeout=self.TIMEOUT, loop=self.bi.loop)
            self.s['writer'].transport.set_write_buffer_limits(low=0, high=0)
        except asyncio.TimeoutError as e:
            warning("Socket Error: Problem connecting to {}:{}".format(tcpip, tcpport))
            raise SPECCommunicationError(expression="connect()", message="Hit an asynio timeout error")
        except:
            warning("connect: BIG Problem connecting to {}:{}".format(tcpip, tcpport))
            warning("connect: Unexpected error in read:", sys.exc_info()[0])
            print("hit exception in connect")
            raise
        else:
            self.connected = True

            info("connect(): done connecting...")
            debug("connect(): {}".format(self.s))
            info("connect(): Socket connected: {}".format(self.connected))


    async def read(self, terminator=None):
        debug("read(): starting")
        if terminator is None:
            terminator = self.RECEIVE_TERMINATOR

        print("terminator:", terminator)
        readBytes = b""
        readStart = time.time()
        try:
            while True:
                #Read the buffer. This is blocking for now
                cBuf = await asyncio.wait_for(self.s['reader'].read(self.BUFFER_SIZE), timeout=self.TIMEOUT, loop=self.bi.loop)
                readBytes += cBuf

                #Test to see if we have made it to the end of the response by looking for the terminator
                if readBytes[(-len(terminator)):] == terminator.encode():
                    debug("Read: '{}'".format(readBytes.decode(self.STR_ENCODING)))
                    break


                #If something goes wrong, we might not get the terminitor that we are expecting.
                if (time.time()-readStart) > self.MAX_READ_TIME:
                    warning("read: terminator not found. Read '{}'".format(readBytes))
                    raise SPECCommandError('read', "Read {} bytes. Terminator not found. data: '{}'".format(len(readBytes), readBytes))

        except asyncio.TimeoutError:
            debug("read: timeout error: read '{}'".format(readBytes))
            raise SPECCommunicationError(expression="read()", message="asyncio timed out")
            raise

        except:
            warning("read(): unexpected error in reading socket:", sys.exc_info()[0])
            raise

        finally:
            debug("read(): returning '{}'".format(readBytes))
            return readBytes

    async def write(self, toSend):
        """Send data to the socket. """
        debug("write(): '{}'".format(toSend))
        try:
            #Write to the streamwriter
            write_result = self.s['writer'].write(toSend) #Returns none on success

            #drain the writer. This should in theory block if the transport hasn't happened yet but I can't get that to work. Right now the wait_for doesn't appear to do anything as the drain routine is not returning a future..
            drain_result = await asyncio.wait_for(self.s['writer'].drain(), timeout=self.TIMEOUT, loop=self.bi.loop)

            debug("write(): drain future: {}".format(drain_result))

        except asyncio.TimeoutError:
            raise SPECCommunicationError(expression="write()", message="asyncio timed out")
        except:
            critical("write: hmmmm.... critical error in write: ",  sys.exc_info()[0])
            raise
            
    def close(self):
        """Just close the socket and set the connected property to false."""
        try:
            debug("close(): closing socket")
            self.s['writer'].close() #Close the writer. this should close the connection
        except:
            warning("close: Error closing socket")
            raise
        else:
            debug("close(): close successful")
            self.connected = False

    def __del__(self):
        """Cleanup the beamline object. Basically, just make sure the socket connection is closed."""
        # debug("called __del__ on beamline interactor")
        self.close()
