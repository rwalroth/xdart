import socket
import time
import types
import sys
import yaml
import copy
import logging
from logging import info, warning, critical, debug
import asyncio


class BL_Variables():
    """Beamline variables are SPEC motors and counters """

    def __init__(self, bi):
        """Setup the BL_Variables object."""

        self.bi = bi

        pass

    class manage_beamline_variables():
        """This is basically a simple set of routines to create all of the motor variables and locate them in a simple object.
        I saw advantages to having both a dictionary and attributes so I am doing both (at least until i make up my mind). The 
        caller can ask for the full dictionary of motor_variaibles or access the motor_variable through an attribute set to the 
        motor_variable name
        
        Rather than having many small functions for each motor register, I have collected all of the necessary information in
        YAML config files and will create them on the fly. Some of the functions have more complex or custom motor interactions
        and those have been overloaded. Those overloaded functions are in motor_variaibles().

        """
        
        def __init__(self, var, bi):
            self.bi = bi

            self.var = var
            self._motor_var_list = []
            self._counter_var_list = []


            asyncio.ensure_future(self.setup_variables(), loop=self.bi.loop)


        def get_variables(self, include_hidden_variables = True):
            """Return the dictionary of motor variables. By default, it returns all variables, including the hidden
            ones. It can also return just the public list. Make more pythonic"""


            if include_hidden_variables is True:
                return self._motor_var_list, self._counter_var_list
            else: #filter the list by the hidden_from_client attribute
                ret_dict = {}


                #This is broken. Don't use
                for (motor_name, motor_var) in self._variables.items():
                    if motor_var.hidden_from_client is False:
                        ret_dict[motor_name] = motor_var

                return ret_dict


        def destroy_all_variables(self):
            """Kaboom! Delete all of the motor variables. This should cleanup/cancel all of the followers as well."""


            for beamline_var in self._counter_var_list:
                del beamline_var

            for beamline_var in self._motor_var_list:
                del beamline_var

        def __del__(self):
            self.destroy_all_variables()


        async def setup_variables(self):
            """Lets read the motors and counters from the beam line and create the variables"""

            #Start by reading the mnemonics
            await asyncio.sleep(1)
            motor_mnemonics = await self.bi.sis.get_all_motor_mnemonics()
            counter_mnemonics = await self.bi.sis.get_all_counter_mnemonics()


            #Loop through the motor mnemonics and create the motor variables
            motor_index = 0
            print("motor mnemonics", motor_mnemonics)
            for new_motor_name in motor_mnemonics:
                motor_var = BL_Variables.variable_object(self.bi, new_motor_name, None, is_motor=True, index_in_read=motor_index)
                print("{}: {}".format(new_motor_name, motor_var))
                setattr(self.var, new_motor_name, motor_var)
                self._motor_var_list.append(motor_var)
                motor_index = motor_index + 1


            #Loop through the counter mnemonics and create the
            counter_index = 0
            for new_counter_name in counter_mnemonics:
                counter_var = BL_Variables.variable_object(self.bi, new_counter_name, None, is_counter=True, index_in_read=counter_index)
                setattr(self.var, new_counter_name, counter_var)
                self._counter_var_list.append(counter_var)
                counter_index = counter_index + 1

            #Set the values for everything
            await self.refresh_variables()


        async def refresh_variables(self, update_counters=True, update_motors=True):
            """ Refresh all or some motor variables. a specific unit can be updated or all variables can be updated by 
            setting unit_to_update=None (default). Updates to certain motor variables may cause updates of others. 
            For example, enabling encoder or changing microsteps will cause variables with units='partial_step' to change 
            at the motor level. Thus, to prevent any significant divergence of the internal state, it can be useful to
            update the internal state to match that of the motor level (just in case we ever get careless and start
            directly accessing the internal cached values (e.g. bypassing the set_function and get_functions). Technically,
            this isn't necessary as any read request will trigger a read of the internal motor register. Still, it seems
            like a good idea to make sure the current cached value is not significantly out of date."""

            all_motor_positions = await self.bi.sis.get_all_motor_positions()
            all_motor_status = await self.bi.sis.get_all_motor_status()

            print("In refresh", self._motor_var_list)
            for motor_index in range(len(all_motor_positions)):
                motor_var = self._motor_var_list[motor_index]

                motor_value = all_motor_status[motor_index]
                motor_value['position'] = all_motor_positions[motor_index]

                motor_var.set_value(None, motor_value)

            all_counters = await self.bi.sis.get_all_counters()

            #Update all the counters
            for counter_index in range(len(all_counters)):
                counter_var = self._counter_var_list[counter_index]
                counter_value = all_counters[counter_index]

                counter_var.set_value(None, counter_value)
            pass



                        
                
    class variable_object():
        """Motor Variables give a place for high-level functions to attach followers (Python Futures) for specific command or oracle frame IDs. 
        When the frame updates the contents of a 'motor variaible', the result is sent to the followers (attached to this specific variable). 
        This function takes a 'description' of the motor_variaible that is being read from a YAML file by another routine ()"""
        def __init__(self, bi, variable_name, var_description, is_motor=None, is_counter=None, index_in_read = None):
            self.MOTOR ="motor"
            self.COUNTER = "counter"

            self.bi = bi #Keep the calling motor interactor as it could be handy
            self.beamline = bi.beamline #Handy to keep a motor object around
            self.followers = {}
            self.last_written_value = None
            self.last_command_id = None
            self.name = variable_name #This is the key used in the description
            self.params = {}

            self.var_type = self.MOTOR if is_motor is True else self.COUNTER

            self.last_changed = time.time()
            self.value = None

            self.index_in_read = index_in_read


            #I should try to load a config file associated w/ the beam line and check if this motor has any special stuff

            if is_motor is True:
                    self.set_function = None #Motor moves get executed in control frames!
                    self.get_function = self.get_motor
            elif is_counter is True:
                    self.set_function = None
                    self.get_function = self.get_counter

            #Create some useful shortcuts that I should probably be loading from a config file
            #self.typecast = self.params['typecast']
            #self.helptext = self.params['Help']
            #self.units = self.params['units']
            #self.hidden_from_client = self.params['hidden_from_client']


            
        def __del__(self):
            print("motor_variable '{}' being deleted. Sending cancel to all followers".format(self.name))
            #send a cancel to all of the futures on all frame IDs
            for frame_uuid in self.followers:
                self.cancel_followers(frame_uuid)
                
            del(self.followers)

        
        
            
        ########################################################################################################################
        # Manage the followers of this variable (add_follower is probably the only one in here anyone will need to call)
        ########################################################################################################################
        
        class return_to_follower():
            """Information to be returned"""
            def __init__(self, future, var):

                self.time_updated = time.time()
                self.value = copy.copy(var.value) #This should't be necessary but just in case the original object gets deleted, just give a copy.
                #self._units = copy.copy(var.units)
                self.future = future

                try:
                    #print("return_to_follower: setting result")
                    future.set_result(self)
                except CancelledError:
                    print("return_to_follower: Future {} was cancelled elsewhere.".format(future))
                except InvalidStateError:
                    print("return_to_follower: Future already done")
                except:
                    print("return_to_follower: bigger problem")
                    raise


        def update_followers(self, frame_uuid):
            """Copy the current result and send it to all of the followers with this specific cmd_uuid. The entire key is removed at the end."""
            #print(" in update")

            try:
                current_followers = self.get_followers(frame_uuid)
                for follower in current_followers:
                    #print("returning to follower")
                    self.return_to_follower(follower, self)
                
                #print("Updated {} followers".format(current_followers))
   
            except KeyError: #No Followers registered for this frame ID
                pass
            except TypeError: #frame_uuid = None or something not found
                #print("frame_uuid not found. No update")
                pass
            else: 
                del(self.followers[frame_uuid])



        def cancel_followers(self, frame_uuid):
            """Cancel all followers with a specific frame ID"""
            for follower in self.get_followers(frame_uuid):
                try:
                    follower.cancel()
                except:
                    pass


        def get_followers(self, frame_uuid):
            """Return the list of followers for the unique Control (or oracle) frame specified. If no followers, return 'None'"""
            try:
                return self.followers[frame_uuid]
            except KeyError:
                return None


        def add_follower(self, frame_uuid, future):
            """Add a follower to this variable. The unique Control (or Oracle) Frame ID needs to be supplied to ensure update happens when scheduled"""
            try: #Add to an existing frame_uuid
                self.followers[frame_uuid].append(future)
            except: #otherwise create the key and assign it to list containing the future
                self.followers[frame_uuid] = [future]

                
                
        ########################################################################################################################
        # Interactions with the motor variables go through the read_value and write_value functions.
        ########################################################################################################################
        async def read_value(self, frame_uuid):
            """Read the value of a variaible using the 'get_function' defined in the config file. The variable 'value'
            is updated and followers with specified frame_uuid are updated. Call with frame_uuid='None' to skip
            updating followers."""

            if self.get_function is not None:
                print("READ VALUE {}: {}".format(self.name, self.get_function))

                overloaded_fn = await self.get_function(frame_uuid)
                return overloaded_fn

            return None
            
        async def write_value(self, frame_uuid, value):
            """Write a value to the motor register using the 'set_function' defined in the config file. The 'get_function' is 
            called to update the 'value' and followers with specified frame_uuid are upddated. Call with frame_uuid='None' to 
            skip updating followers. Custom responses may be possible depending on implementation"""
            
            #Call the (possibly) overloaded function to write a value to a variable.
            if self.set_function is not None:
                await self.set_function(value, frame_uuid)
            
            #Trigger the read of the new value and return it to the user. This function will also trigger an update for the followers.

            return(await self.read_value(frame_uuid))
        
        def set_value(self, frame_uuid, value):
            """Set the value of the motor and update followers. Set frame_uuid to 'None' to avoid updating any followers. This function 
            should only appear when creating custom motor variable register read/write routines (e.g. read_many_vars or the custom_get_software_limits)"""
            
            
            self.value = value
            self.last_changed = time.time()

            #print(value)
            self.update_followers(frame_uuid)

        ########################################################################################################################
        # Default functions to set and get variable infromation directly from the motors and counters
        ########################################################################################################################


        async def get_motor(self, frame_uuid=None):
            """Get the position and status of a single motor"""


            motor_pos = await self.bi.sis.get_motor_position(self.name)
            motor_status = await self.bi.sis.get_motor_information(self.name)

            new_value = motor_status
            new_value['position'] = motor_pos

            #set the value and update the followers
            self.set_value(frame_uuid, new_value)

            return new_value

        async def get_counter(self, frame_uuid=None):
            """Get the value of a counter. Note: all the counters are read. While only one counter is returned, all are actually updated since we have the information"""

            all_counters = await self.bi.sis.get_all_counters()

            #Update all the counters
            for counter_index in range(len(all_counters)):
                counter_var = self.variables._counter_var_list[counter_index]
                counter_value = all_counters[counter_index]

                counter_var.set_value(frame_uuid, counter_value)

            return all_counters[self.index_to_read]




