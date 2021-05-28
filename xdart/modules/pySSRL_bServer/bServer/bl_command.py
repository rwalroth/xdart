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


class BLCommand():
    """A class to keep track of each beamline interaction: a command and (potentially) response.  
    Keep track of whether there was an error and keep track of the list of responses 

    I plan to keep track of the counterUser variable in here so I can verify 

    """
    def __init__(self, beamline, command, sendterminator=None, readterminator=None, listSeparator=None, needsResponse=False, pauseAfterWrite=None, pauseAfterRead=None):

        self.beamline = beamline
        self.command = copy.copy(command)

        self.needsResponse = needsResponse is True
        self.response = []

        self.readterminator = copy.copy(readterminator)
        self.sendterminator = copy.copy(sendterminator)
        self.listSeparator = copy.copy(listSeparator)

        if pauseAfterWrite is not None:
            self.pauseAfterWrite = copy.copy(pauseAfterWrite)
        else:
            self.pauseAfterWrite = 0
        
        
        if pauseAfterRead is not None:
            self.pauseAfterRead = copy.copy(pauseAfterRead)
        else:
            self.pauseAfterRead = 0
        
        self.writeSuccess = False
        self.readSuccess = False

        self.senderror = False
        self.readerror = False
        self.fatalerror = False

        self.timeCreated = time.time()


        
    def __del__(self):
        pass
    

    async def execute(self):
        """This function should execute a single command and read the value if required
        (basically, go through and execute everything necessary for the beamline interaction)"""

        #print("executing cmd")
        #Keep the commands in the queue
        #self.beamline.completedCommands.append(self)

        try: #Try to execute the command
            debug("execute: '{}'".format(self.command))
            #print('try')
            await self.beamline.writeCommand(self.command, terminator=self.sendterminator)
            #print('sent')
        except: #If we pick up an error, return the error and set the send error flag
            warning("Problem writing command")
            self.senderror = True
            raise
            
        else: #If the send goes well, set the write suceess flag and check to see if we need a response
            self.writeSuccess = True
            self.timeWritten = time.time()
            debug("execute: command written")

            try: #Wait after write if this has been requested
                await asyncio.sleep(self.pauseAfterWrite)
            except:
                debug("execute: error waiting")
                raise

            
            if self.needsResponse is True: #If a response is needed
                try: #Try to read the response
                    debug("execute: Reading response")
                    self.response = await self.beamline.readResponse(terminator = self.readterminator, listSeparator = self.listSeparator)
                except: #If we get an error, we should do something about it. For now lets just pass it
                    debug("")
                    self.readerror = True
                    raise
                else: #If the read goes well, set 
                    debug("execute: response read")
                    self.readSuccess = True
                    self.timeRead = time.time()
                    
                    try: #do a pause after the read if requested
                        await asyncio.sleep(self.pauseAfterRead)
                    except:
                        pass
                
            
        return

    def toSequence(self):
        """Create a command sequence containing only this command. This will be very useful for sequence addition"""
        newSequence = BL_CommandSequence(singleCommand=self)

        return newSequence
    

    def __repr__(self):
        """Representation of the current object"""
        res = []
        
        res.append("Command: {}".format(self.command))
        
        res.append("Response: {} items".format(len(self.response)))
        for m in self.response:
            res.append(" '{}'".format(m))
            
        return("\n".join(res))

    def typecastResponse(self, typecastList):
        """Return the typecast form of the response. This is a little lazy. Try harder..."""
        #print("response: {}".format(self.response))
        if len(typecastList) != len(self.response): #This is a pretty basic error check.... if the beamline doesn't return the right number of parameters, we should throw a beamline error and let it try to recover or quit.
            raise(BLCommandError('typecastResponse', "cmd '{}' response '{}' typecastList '{}' ".format(self.command, self.response, typecastList)))

        converted_response = []
        for ctr in range(len(typecastList)):
            current_response = self.response[ctr]
            current_typecast = typecastList[ctr]

#            print(current_response)
#            print(current_typecast(current_response))

            if current_typecast == bool: #Turns out bool("0") is True... in fact any string returns true. Convert to integer and then to bool
                converted_response.append( bool(int(current_response)))
            else:
                converted_response.append(current_typecast(current_response))


        #print(converted_response)
        return converted_response
        
        
    
    def __add__(self, nextSeq): 
        """Added commands must be converted to sequences. This routine gets called if a command is on the left
        and prevents python from messing up the order of operations."""
        newSequence = BL_CommandSequence(singleCommand=self)
        
        #Once the first command has been converted to a sequence, we can call the normal CommandSequence version of add
        newSequence = newSequence + nextSeq 
        
        return newSequence
                    




class BL_CommandSequence():
    def __init__(self, singleCommand = None):
        
        self.commandList = []
        
        if singleCommand is not None:
            self.commandList.append(singleCommand)
        
        self.current = 0
        
        return
    
    
    def __add__(self, nextSeq): 
        """Add a command sequence to a command sequence or a single command with 'self' preceeding 'nextSeq' in the 
        list. While order of operations matters, we have overloaded the 'add' function of the LMD_command class so 
        we are guaranteed to always have the correct ordering"""
        
        newSequence = BL_CommandSequence()

        
        try: # If a command was passed as a CommandSequence, lets convert it to a sequence with only this command
            nextSeq = nextSeq.toSequence()
        except: #If there is an exception, we just keep moving on
            pass
        
        for cCmd in self.commandList: #Add the 'self' sequence first
            newSequence.commandList.append(cCmd) 
        
        for cCmd in nextSeq.commandList: #Add the 'nextSeq' after this
            newSequence.commandList.append(cCmd)
        
        return newSequence
        

#    def __radd__(self, aCmd): #This is not necessary because we put in an __add__ for the LMD_Command. We should never need to wory about operator presecend

    
    def __iadd__(self, nextSeq):
        """An inplace add will convert a command to a sequence if necessary and then append it to the end of a current object"""
        try:
            nextSeq = nextSeq.toSequence()
        except:
            pass
        
        for cCmd in nextSeq.commandList:
            self.commandList.append(cCmd)
        
        return(self)

    
    
    def __getitem__(self, index):

        try:
            rCmd = self.commandList[index]
        except IndexError:
            raise
        else:
            return rCmd

    def __setitem__(self, index, value):
        try:
            self.commandList[index] = value
        except IndexError:
            raise
    
    def __delitem__(self, index):
        try:
            self.commandList.remove(index)
        except IndexError:
            raise
        
    def __len__(self):
        return( len(self.commandList))
    
    def __repr__(self):
        """Representation of the current object"""
        res = []
        
        for m in self.commandList:
            res.append(m.__repr__())
            
        return("\n".join(res))
    
    async def execute(self):
        """Execute a sequence of commands"""
        for currentCommand in self.commandList:
            try:
                await currentCommand.execute()
            except:
                print("error in command.execute: {}".format(sys.exc_info()[0]))
                raise
            else:
                pass

        return

