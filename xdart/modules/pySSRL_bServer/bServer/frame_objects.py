import socket
import time
import types
import sys
import yaml
import copy
import logging
from logging import info, warning, critical, debug
import asyncio
from contextlib import contextmanager
import sys, traceback


class FrameObject():
    """Inheritable class with functions common to the Control and Oracle Frames. """

    def _common_init(self, frame_pool, bi_list):
        """Takes care of creating the standard set of start/stop futures, cleaning up the frame_list in the frame pool,
         creating queues for followers, and adding the frame to the frame pool."""
        #Keep a reference to the FramePool object


        #print("here")
        self.frame_pool = frame_pool

        self.mi_list = mi_list

        #print('before cleanup')
        #house cleaning
        self.frame_pool.cleanup_frame_list()

        #print('after cleanup')

        #Create a finished flag
        self.flag_finished = False

        #Init the delete me flag to False
        self.flag_delete = False

        #Store the time of creation
        self.time_created = time.time()

        #queue for the followers. Not sure if I need this in the control frame as well.... could be useful in the cleanup?
        self.follower_queue = asyncio.Queue(loop=self.frame_pool.loop)

        #Generate the unique ID for the Frame
        self.frame_uuid = self.frame_pool.generate_frame_uuid()

        # Enable followers to attach. This should only be disabled right before cleanup of the Control and oracle
        # frames. and enabled at the end of the init routine of the control / oracle frames
        self.allow_attachement = False

        #Create a place to store all of the followers and the associated futures
        self.followers = {}

        #Create the start and stop future objects. ensure the results
        self.start_future = {}
        self.end_future = {}
        self.init_all_futures()

        #Add the start futures to the bi_list
        self.add_start_to_bi_queues()

        #Add the new frame to the frame_pool frame_list
        self.frame_pool.frame_list.append(self)

        debug('common_init: done ')


    def generate_follower_uuid(self):
        """generate unique frame IDs. This is realtively easy to do since all ID's for all motors are generated
         by a single instance of FramePool. This is an 8-digit hexadecimal number which gives us 4,294,967,296 values before
         the sequence could repeat. Since each command takes ~10ms at least, it would take roughly 500 days for something to happen....
         Actually, nothing would happen because commands that old would be taken care of by the garbage collector long long long before
         that happened. """

        follower_uuid = uuid.uuid4().hex[:8].upper()
        return follower_uuid

    def init_all_futures(self):
        """Create a start and stop future along with a 'signal' in case we need to cancel or alert the async routine
        while running"""

        # Create a signal in case we need to cancel the command or some form of external communication
        self.external_signal = asyncio.Future(loop=self.frame_pool.loop)
        asyncio.ensure_future(self.external_signal, loop=self.frame_pool.loop)

        # Create the start/end
        for bi in self.bi_list:
            #initialize future objects
            new_start_future = asyncio.Future(loop=self.frame_pool.loop)
            new_end_future = asyncio.Future(loop=self.frame_pool.loop)

            #ensure these - basically register them with the event loop?
            asyncio.ensure_future(new_start_future, loop=self.frame_pool.loop)
            asyncio.ensure_future(new_end_future, loop=self.frame_pool.loop)

            #save these in the Frame object
            self.start_future[bi.pulpit] = new_start_future
            self.end_future[bi.pulpit] = new_end_future


    def __del__(self):
        """Remember to cancel all"""
        #cancel all the pending futures from this object.
        pass

    def add_start_to_bi_queues(self):
        """Add the start futures"""

        pass



    def attach_followers(self, var_list):
        """Add each variable to the follower. We will add a 'request_uuid' and save all the futures/vars in a struct. The ability to still attach is checked. Thus, a request is specified by both a frame and request uuid"""
        #print("attaching followers:")

        if self.allow_attachement is False:
            debug("attach_followers: Returning false")
            return None


        #print("starting attachement")

        ret_dict = {}
        for follower_var in var_list:
            #Create a new future for the follower
            new_future = asyncio.Future(loop=self.frame_pool.loop)
            asyncio.ensure_future(new_future, loop=self.frame_pool.loop)

            #Add the followers to the variable
            follower_var.add_follower(self.frame_uuid, new_future)

            #record this information with the future as the key and the variaible as the value
            ret_dict[new_future] = follower_var

        #Assign a unique request ID to identify this transation. Probably overkill, but this is to allow other other following requests to attach and be identifiable (variables may be accessed multiple times in different requests)
        request_uuid = self.generate_follower_uuid()  # something the user can use to retrieve the answer if the know the frame_uuid
        self.followers[request_uuid] = ret_dict

        #print("done attaching followers")

        return request_uuid, ret_dict


    async def get_request_data(self, requestID):
        """Read the data associated with requestID."""

        try:
            request_dict = self.followers[requestID]
        except KeyError:
            return None

        data = {}
        for (future, motor_var) in request_dict.items():
            debug("get_request_data: waiting for '{}' : {}".format(motor_var.name, future))
            await future
            f_result = future.result()
            data[motor_var] = f_result.full_results


        return data

    def request_finished(self, requestID):
        """Check the futures associated w/ this request. NON BLOCKING. Returns None if requestID is invalid. Retursn False if not finished. Returns True if all futures are finished."""

        try:
            request_dict = self.followers[requestID]
        except KeyError:
            return None

        #Check all of the futures associated with the request
        for (future, motor_var) in request_dict.items():
            if future.done() is False: #If one isn't done, we return false.
                return False

        #All of them are done.
        return True

    def allows_followers(self, required_variables): #This is overloaded
        return False

    def attach_pulpits(self):
        """Add the current frame to all of the pulpit objects associated with this object. Currently, this is all of
        the motor interactor objects that this frame is set to follow. Ideally, there should be sub-objects within
        the motor interactor (in case we can have multiple concurrent things accessing a single MI)"""
        #Add the frame to the pulpit
        for bi in self.bi_list:
            bi.pulpit.add_frame(self)






    async def wait_for_pulpit(self, *args, **kwargs):
        """Wait on the futures of this object until they are set by the pulpit"""
        print("wait_for_pulpit: kwargs: {}".format(kwargs))
        try:
            msg = kwargs['msg']
        except KeyError:
            msg = ""

        print("Starting {}".format(msg), self)
        for (pulpit_obj, future) in self.start_future.items():
            print("{} checking future. Future: {}  Pulpit: {}".format(msg, future, pulpit_obj))
            if future.done() is False:
                print('  waiting on Future')
                await future
            else:
                print('  continuing')


    def step_off_pulpit(self, *args, **kwargs):
        print("step_off_pulpit: starting")
        try:
            msg = kwargs['msg']
        except KeyError:
            msg = ""

        print('setting end futures')
        #Set the end routines
        for (pulpit_obj, future) in self.end_future.items():
            #print("run_move_position setting end. Future: {}  Pulpit: {}".format(future, pulpit_obj))
            future.set_result("  finished {}".format(time.time()))
            print("  end future set ", future)

        self.flag_finished = True


    #######################################################################################
    # Decorators for frame objects to take care of the annoying details and error handling
    #######################################################################################

    def add_pulpit_control_flow(frame_function):
        """Adds control flow for the pulpit objects. This should be the first decorator around any function that
        uses the pulpits"""
        async def pulpit_control_wrapper(self, *args, **kwargs):
            debug('add_pulpit_control: starting')
            # The 'msg' keyword is used.
            try:
                msg = kwargs['msg']
            except KeyError:
                msg = None

            try:
                debug('add_pulpit_control: starting wait_for_pulpit')
                print('add_pulpit_control: kwargs: {}'.format(kwargs))
                print('add_pulpit_control: self: {}'.format(self))
                print('add_pulpit_control: msg: {}'.format(msg))
                await self.wait_for_pulpit(self, msg=msg)

                debug('add_pulpit_control: running frame_function')
                ret_val = await frame_function(self, *args, **kwargs)

            except ExitCommandGracefully as e:
                debug('Trying to exit command gracefully: {}'.format(e.msg))


                self.flag_error = True
                self.error_message = e.msg

            except:
                debug("add_pulpit_control: got an error that cannot be handled: ", sys.exc_info()[0])

                exc_type, exc_value, exc_traceback = sys.exc_info()
                exc_type, exc_value, exc_traceback = sys.exc_info()
                print("*** print_tb:")
                traceback.print_tb(exc_traceback, limit=2, file=sys.stdout)
                print("*** print_exception:")
                # exc_type below is ignored on 3.5 and later
                traceback.print_exception(exc_type, exc_value, exc_traceback,
                                          limit=2, file=sys.stdout)
                print("*** print_exc:")
                traceback.print_exc(limit=2, file=sys.stdout)
                print("*** format_exc, first and last line:")
                formatted_lines = traceback.format_exc().splitlines()
                print(formatted_lines[0])
                print(formatted_lines[-1])
                print("*** format_exception:")
                # exc_type below is ignored on 3.5 and later
                print(repr(traceback.format_exception(exc_type, exc_value,
                                                      exc_traceback)))
                print("*** extract_tb:")
                print(repr(traceback.extract_tb(exc_traceback)))
                print("*** format_tb:")
                print(repr(traceback.format_tb(exc_traceback)))
                print("*** tb_lineno:", exc_traceback.tb_lineno)

                raise
            else:
                return ret_val
            finally:
                debug('add_pulpit_control: stepping off pulpit')
                self.step_off_pulpit(self, msg=msg)

                print('add_pulpit_control: EVERYTHING IS DONE')

        return pulpit_control_wrapper

    def repeat_until_complete(frame_function):
        """Decorator to call a function until finished. Repeat if it returns a RetryCommand error. Otherwise, raise it up."""
        async def repeat_func(self, *args, **kwargs):
            debug('repeat_func: starting')
            while True:
                try:
                    ret_val = await frame_function(self, *args, **kwargs)
                except RetryCommand:
                    #Let the loop go again
                    pass
                except:
                    raise
                else:
                    debug("repeat_until_complete: done repeating. returning '{}'".format(ret_val))
                    self.flag_finished = True
                    return ret_val

        return repeat_func



    def handle_motor_config_error(frame_function):
        async def restore_motor_config(self, *args, **kwargs):
            """Check that all the ecessary motors have a valid (non-zero) config. This will only happen in the case of power cycling."""
            debug('handle_motor_config_error: starting')
            for mi in self.mi_list:
                print("Checking motor_config of {}".format(mi.motor_name))
                #Record the current motor state before updating user_register_two
                current_persistent_state = mi.motor_config.peek_at_persistent_variables()
                current_config = await mi.motor_variables.user_register_two.read_value(None)

                #Just make sure the original value is restored. Shouldn't be necessary but lets just avoid any potential problems
                mi.motor_variables.user_register_two.value = current_persistent_state['user_register_two']

                if current_config == 0: #There should never be any configuration when a value of zero is actually allowed as the uuid
                    debug("handle errors: restoring motor {} from memory".format(mi.motor_name))
                    debug("***** If this is looping, it means there is somehow a zero saved in the persistent_state. This should never happen but if this restoring keeps looping, just delete the persistent configs - reloading from the base config (which never should have a uuid of zero) should fix all the problems")
                    await mi.motor_config.restore_persistent_state_from_array(current_persistent_state)
                    raise RetryCommand(message='Config applied. Retrying Command')

            ret_val = await frame_function(self, *args, **kwargs)
            return ret_val

        return restore_motor_config


    def handle_communication_errors(frame_function):
        """Try fixing things if an error occurs during a frame. Reconnecting or reissuing a command. Return True if no errors are caught"""
        async def wrapper_handle_comm_error(self, *args, **kwargs):
            debug('handle_communication_errors: starting')
            try:
                msg = kwargs['msg']
            except KeyError:
                msg = ""
            debug('handle_communication_errors: getting ready to start')

            try:
                debug("{}: handle_errors: starting {}".format(msg, frame_function.__name__))
                ret_val = await frame_function(self, *args, **kwargs)

            except (ConnectionResetError, asyncio.TimeoutError, MotorCommunicationError, MotorCommandError) as e:
                #This catches basically all possible connection issues. Just need to reconnect to the motor and then we can keep going
                try:
                    critical("{} : reconnecting in handle_frame_errors: {}".format(msg, e))
                    for mi in self.mi_list:
                        while True:
                            critical("{}: Reconnecting to {}".format(msg, mi.motor_name))
                            try:
                                await mi.motor.reconnect()
                            except (asyncio.TimeoutError, MotorCommunicationError, MotorCommandError):  #
                                critical("{}: Hit a timeout error in the handle_frame_errors during reconnect".format(msg))
                            else:
                                critical("{}: Reconnected".format(msg))
                                #Once we actually connect, lets kick out of the loop for this motor interactor
                                break
                except:
                    raise
                else:
                    critical("Everything reconnected")
                    raise RetryCommand(message='Motors reconnected. Retrying command')
            except:
                raise
            else:
                debug("{}: handle_errors: everything worked".format(msg))
                return ret_val

            finally:
                debug("{}: handle_errors: finished".format(msg))

        return wrapper_handle_comm_error

    def update_orphaned_followers_afterwards(frame_function):
        """The mini-oracle update routine that updates any followers associated with this frame_uuid. Never leave a follower hanging!"""
        async def mini_oracle_frame(self, *args, **kwargs):
            debug('update_orphaned_followers_afterwards: starting')
            #Call the actual functon
            ret_val = await frame_function(self, *args, **kwargs)

            debug("mini_oracle_frame: stopping attachement")

            # Stop attachement
            self.allow_attachement = False

            t0 = time.time()
            total_followers = 0
            for mi in self.mi_list:
                var_dict = mi.motor_variables.get_motor_variables()
                # print(var_dict)
                for (var_name, motor_var) in var_dict.items():  # This is a little clunky but will work
                    # print("Looking at {}: {}".format(var_name, motor_var))
                    # Technically, we could just run the update routine... but lets check so we can be sure what we are updating...
                    num_followers = motor_var.get_followers(self.frame_uuid)
                    # print(" num_followers: ", num_followers)
                    if num_followers is not None:
                        print("Updating followers of variable '{}' on motor '{}'".format(var_name, motor_var.name))
                        await motor_var.read_value(self.frame_uuid)
                        print("  updating {}: {}s".format(motor_var.name, time.time() - t0))
                        total_followers = total_followers + 1
                        # motor_var.update_followers(oracle_frame.frame_uuid)

            print("mini_oracle_frame: total followers = {}\n\n\n\n\n\n\n".format(total_followers))
            return ret_val

        return mini_oracle_frame