import socket
import time
import types
import sys
import yaml
import copy
import logging
from logging import info, warning, critical, debug
import asyncio
import re

sys.path.append('C:\\Users\\Public\\repos\\xdart')

from xdart.modules.pySSRL_bServer.bServer.bl_communication import *
from xdart.modules.pySSRL_bServer.bServer.bl_command import *
from xdart.modules.pySSRL_bServer.bServer.BL_Error import *
from xdart.modules.pySSRL_bServer.bServer.PulpitObject import *
from xdart.modules.pySSRL_bServer.bServer.BL_Variables import *

class BL_Interaction():
    """This class is holds all of the beamline interaction objects and initilizes all of
    their functionality. This includes the beamline variables, rosetta object, beamline state configuration object, and
    subroutines for executing commands on the beamlines. Each beamline will have it's own LMD_beamlineInteraction()
     object."""
    
    def __init__(self, beamline_name, loop):
        """Sets up all of the objects discussed above. The only argument is the 'fun' unique name of the beamline that
        appears in the beamline config YAML files."""

        #Lets save the "fun" name
        self.beamline_name = beamline_name

        #Save a pointer to the loop for all the async functions
        self.loop = loop

        #Do the rest of the initialization in an async function - can't be done directly in __init__ since async tag is not allowed
        asyncio.ensure_future(self.setup(), loop=self.loop)



    async def setup(self):
        """Setup anything that depends on async functionality be available"""

        # Initialize the beamline communciations
        try:
            self.beamline = BL_SPEC(self)
            await self.beamline.setup()
            print("Finished beamline setup for '{}'".format(self.beamline_name))
        except:
            print("Caught exception in setup of beamline communication")
            raise RuntimeError("Caught exception in setup of communication for '{}': {}".format(self.beamline_name, sys.exc_info()[0]))

        #Get the mnemonic
        self.mnemonic = self.beamline.mnemonic


        #Lets initialize the SPEC Infoserver Interaction.
        try:
            print("interface:: '{}'".format(getattr(self.beamline, 'interface')))
            if self.beamline.interface == "SPEC Infoserver":
                print("starting beamline interface")
                debug("Setting up beamline interface for {}".format(self.beamline_name))

                self.sis = self.SPECInfoserverInteraction(self)
                print("done starting beamline interface")
            else:
                debug("Could not find correct interface for {}".format(self.beamline_name))
                raise RuntimeError("Could not find the correct interface to initialize")
        except:
            print("Caught exception starting SPEC Infoserver Interaction Class: {}".format(sys.exc_info()[0]))
            raise RuntimeError("Caught exception in setup of SPEC Infoserver Interaction for'{}': {}".format(self.beamline_name, sys.exc_info()[0]))



        # Lets refresh all of the values in the beamline registers
        debug("bl_interaction: init beamline variables")
        self.variables = BL_Variables(self)

        self.variables.manage_beamline_variables(self.variables, self)



        #await self.beamline_variables.refresh_variables()

        #create the pulpit objects. This framework uses multiple pulpits since the SIS framework actually has a few different ways of getting info
        self.command_pulpit = PulpitObject(loop=self.loop)
        self.motor_info_pulpit = PulpitObject(loop=self.loop)
        self.counter_pulpit = PulpitObject(loop=self.loop)

        #Create a lock for the communication and execute of commands for this beam line. This is necessary since we have multiple pulpits and socket communication may need to be grouped to prevent issues with our concurrancy framework from giving the wrong information between concrurrent commands (or trying to execute concurrently)
        self.beamline.comm_lock = asyncio.Lock(loop=self.loop)

    class SPECInfoserverInteraction:
        """Low level SPEC infoserver commands. These are just out of the SPEC infoserver doc"""
        def __init__(self, bi):
            debug("SPECInfoserverInteraction: init()")
            self.bi = bi
            self.beamline = bi.beamline

            #SIS has a bunch of canned text responses. Lets put them in once as a variable within the class so we don't make any mistakes when comparing values
            self.sis_text = {}
            self.sis_text['in_control'] = "client in control."
            self.sis_text['not_in_control'] = "client not in control."
            self.sis_text['control_not_available'] = "control not available."
            self.sis_text['logging on'] = "Logging is ON."
            self.sis_text['logging off'] = "Logging is OFF."

        
        async def get_version(self):
            """Run the ?ver command for spec infoserver"""
            cmd_text = "?ver"

            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True)

            await cmd.execute()
            print("cmd: {}".format(cmd))
            response = cmd.response[0]
            return response


        async def get_user(self):
            """Run the ?usr command for spec infoserver"""
            cmd_text = "?usr"

            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True)

            await cmd.execute()

            response = cmd.response[0]
            return response


        async def get_console_output_buffer(self, N=None, return_after=False, get_buffer_index=False):
            """Run the ?usr command for spec infoserver"""

            if N is None and get_buffer_index is False:
                cmd_text = "?con"
            elif N is None and get_buffer_index is True:
                cmd_text = "?con idx"
            elif N is not None and return_after is True:
                cmd_text = "?con {}-".format(N)
            elif N is not None and return_after is False:
                cmd_text = "?con {}".format(N)

            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True, listSeparator="\n")

            await cmd.execute()

            if  N is None and get_buffer_index is True:
                response = int(cmd.response[0])
            else:
                response = cmd.response


            return response


        async def is_available(self):
            """Run ?avl. Check if SPEC is available."""

            cmd_text = "?avl"
            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True)
            await cmd.execute()

            availability = cmd.typecastResponse([bool])[0]

            return availability


        async def is_busy(self):
            """Run ?bsy. This is the opposite of ?avl. Check if spec is busy."""
            cmd_text = "?bsy"
            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True)
            await cmd.execute()

            busy = cmd.typecastResponse([bool])[0]

            return busy


        async def get_motor_position(self, motor_name):
            """Run ?mp"""

            cmd_text = "?mp {}".format(motor_name)
            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True)
            await cmd.execute()

            response = cmd.typecastResponse([float])[0]
            return response


        async def get_motor_information(self, motor_name):
            """Run ?mi and get the motor info. Parse result and return a dict"""

            cmd_text = "?mi {}".format(motor_name)
            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True)
            await cmd.execute()

            response = cmd.typecastResponse([int])[0]

            mi_dict = self.decode_motor_status_bits(response)

            return mi_dict


        def decode_motor_status_bits(self, status):
            """Decode the 4-bit state of the motor. See SPEC infoserver doc. Returns a dictionary"""
            mi_dict = {}
            mi_dict['motor moving'] = True if status & 0x1 else False
            mi_dict['motor disabled'] = True if status & 0x2 else False
            mi_dict['low limit active'] = True if status & 0x4 else False
            mi_dict['high limit active'] = True if status & 0x8 else False

            return mi_dict


        async def get_all_motor_mnemonics(self):
            """Get all of the motor names as a list"""
            cmd_text = "?mne"
            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True, listSeparator=", ")
            await cmd.execute()
            response = cmd.response

            print(cmd)
            print(response)
            return response


        async def get_all_counter_mnemonics(self):
            """Get all of the counter names as a list. This is undocumented in the SIS documentation but I found it in Stefans code."""
            cmd_text = "?mne c"
            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True, listSeparator=", ")
            await cmd.execute()
            response = cmd.response

            return response


        async def get_all_motor_positions(self):
            """Get all motor positions"""

            cmd_text = "?mpa"
            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True, listSeparator=", ")
            await cmd.execute()

            #Could have done the listSeparator above
            response = cmd.response
            converted_response = [float(x) for x in response]

            return converted_response


        async def get_all_motor_status(self):
            """Get all motor positions"""

            cmd_text = "?mia"
            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True, listSeparator=", ")
            await cmd.execute()

            response = cmd.response

            all_motor_status =[]
            for motor_status in response:
                all_motor_status.append(self.decode_motor_status_bits(int(motor_status)))

            return all_motor_status


        async def get_all_counters(self):
            """Get all motor positions"""

            cmd_text = "?cta"
            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True, listSeparator=", ")
            await cmd.execute()

            response = cmd.response
            converted_response = [float(x) for x in response] #Is floating point the right thing? I guess....

            return converted_response


        async def get_detector_status(self):
            """Get the detector status string. Not sure what this actually is"""

            cmd_text = "?det"
            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True, readterminator='\r\n')
            await cmd.execute()

            response = cmd.response[0]
            print(cmd)
            return response


        async def get_all_status_motors_and_counters(self):
            """This function will eventually return everything that is returned by ?all. Right now, not sure what the
            counter statuses actually mean. Returning the string right now."""
            cmd_text = "?all"
            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True, listSeparator=", ")
            await cmd.execute()

            response = cmd.response
            #converted_response = [float(x) for x in response] #Is floating point the right thing? I guess....

            return response


        async def get_current_scan_details(self):
            """Get the detector status string. Not sure what this actually is"""

            cmd_text = "?sci"
            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True, readterminator='\r\n')
            await cmd.execute()

            response = cmd.response[0]
            print(cmd)
            return response


        async def get_current_plot_point_index(self):
            """Return the current buffer index"""
            cmd_text = "?plt idx"
            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True)
            await cmd.execute()

            response = cmd.response[0]
            print(cmd)
            return response


        async def get_plot_points(self, num_pts = None):
            """Return the full buffer or the last 'num_pts' points. Default is the full buffer"""

            if num_pts is not None: #return the last num_pts points
                cmd_text = "?plt {}".format(num_pts)
            else: #Get everything
                cmd_text = "?plt all"

            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True, listSeparator="/")
            await cmd.execute()

            response = cmd.response
            print("len response: {}".format(len(response)))
            converted_response = []
            t0 = time.time()
            for data_series in response:
                #c_line = list(map(float, data_series.split(", ")))
                c_line = data_series.split(", ")
                converted_response.append(c_line)

            print("conversion took {}sec".format(time.time()-t0))

            return converted_response


        async def are_we_in_control(self):
            """Check if we already have control."""
            cmd_text = "?inc"
            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True)
            await cmd.execute()

            inc = cmd.typecastResponse([bool])[0]

            return inc


        async def get_remote_control(self):
            """Get the current plot. Not sure what this actually is"""

            cmd_text = "!rqc"
            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True)
            await cmd.execute()

            response = cmd.response[0]
            print(response)
            return response


        async def release_remote_control(self):
            """Get the current plot. Not sure what this actually is"""

            cmd_text = "!rlc"
            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True)
            await cmd.execute()

            response = cmd.response[0]
            print(response)
            return response


        async def execute_unix_command(self, unix_cmd):
            """Get the current plot. Not sure what this actually is. untested"""

            cmd_text = "!unx {}".format(unix_cmd)
            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True)
            await cmd.execute()

            response = cmd.response[0]

            m = re.match(r"(\d+), (.*)", response, re.DOTALL) #DOTALL catches newline characters as well", response)
            if m is not None:
                cmd_success = bool(int(m.groups()[0]))
                ret_val = m.groups()[1]
                debug("execute_unix_command: success = {}, response = '{}'".format(cmd_success, ret_val))

                return {'success': cmd_success, 'response': ret_val}
            elif response == self.sis_text['not_in_control']:
                raise SISControlError(msg='execute_unix_command: not in control. Raising error')
            else:
                raise SPECCommandError(msg="execute_unix_command: unknown response: '{}'".format(response))

            print(response)
            return response


        async def abort_command(self):
            """Abort the current SPEC command - equivelent to Ctrl^C"""
            cmd_text = "!abr"
            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True)
            await cmd.execute()

            #can return not in control!
            response = cmd.response[0]
            print(response)
            return response


        async def execute_command(self, spec_cmd):
            """Execute a spec command and return the uuid of the command. In the case of SIS, this just an increasing
            number."""
            cmd_text = "!cmd {}".format(spec_cmd)

            debug("execute_command: executing '{}'".format(cmd_text))

            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True)
            await cmd.execute()

            response = cmd.response[0]
            debug("execute_command: received'{}'".format(cmd_text))

            m = re.match(r"#(\d+)", response)
            if m is not None:
                spec_cmd_uuid = int(m.groups()[0])
                debug("execute_command: command executed as #{}".format(spec_cmd_uuid))
                return spec_cmd_uuid
            elif response == self.sis_text['not_in_control']:
                raise SISControlError(msg='execute_command: not in control. Raising error')
            else:
                raise SPECCommandError(msg="execute_command: unknown response: '{}'".format(response))


        async def retrieve_result(self):
            """Get the most recent result from SIS. Sadly SIS only keeps track of the most recent result. Returns just the last one in memory. Does not block in any way."""
            cmd_text = "?res"

            debug("retrieve_result: sending")

            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True)
            await cmd.execute()

            response = cmd.response[0]
            debug("retrieve_result: response '{}'".format(response))

            spec_result = {}
            m = re.match(r"#(\d+), (\w+), (.*)", response, re.DOTALL) #DOTALL catches newline characters as well
            if m is not None:
                matched = m.groups()
                spec_result['uuid'] = int(matched[0])
                spec_result['status ok'] = True if matched[1] == "OK" else False
                spec_result['result'] = matched[2]
            else:
                raise SPECCommandError(message="retrieve_result: Got a result we couldn't parse")

            debug('retrieve_result: parsed: {}'.format(spec_result))
            return spec_result


        async def set_sis_logging(self, set_logging_on=None):
            """This is a poorly documented feature that appears to return enteries in the SIS log. Could be useful for
            debugging or potentially getting the response of commands in case we miss calling the ?res before executing
            another command. Need to experiment. untested"""

            if set_logging_on is None:
                set_logging_on = True

            if set_logging_on is True:
                cmd_text = "!log on"
                debug('set_sis_logging: turning on')
            else:
                cmd_text = "!log off"
                debug('set_sis_logging: turning off')

            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True)
            await cmd.execute()

            response = cmd.response[0]
            debug("set_sis_logging: response '{}'".format(response))

            if response == self.sis_text['logging on'] and set_logging_on is True:
                pass
            elif response == self.sis_text['logging off'] and set_logging_on is False:
                pass
            else:
                print("response vs loggingoff:", response == self.sis_text['logging off'])
                raise SPECCommandError(message="set_sis_logging: unknown response: '{}'".format(response))

            return response


        async def get_sis_logs(self, num_entries=None):
            """A poorly documented feature that appears to return entries of SIS logging.
            Specifiy either the number of recent entries to return or 'None' to return the full log.
            I believe this is capped at 1000 entries  from Stefan's code. untested"""

            debug('get_sis_logs: starting')
            if num_entries is not None: #return last N
                cmd_text = "!log {}".format(num_entries)
            else: #return everything
                cmd_text = "!log"

            cmd = BLCommand(self.beamline, cmd_text, needsResponse=True, listSeparator="\n")
            await cmd.execute()

            response = cmd.response
            debug("get_sis_log: response '{}'".format(response))

            return response


    ###################################################################################
    # Universal Functions
    ###################################################################################


    ######################################################################################
    # Lets add some fast diagnostic functions. These will rely on the get_many_vars
    ########################################################################################
