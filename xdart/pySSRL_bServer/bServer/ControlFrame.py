
import asyncio
import sys, traceback


class ControlFrame(FrameObject):

    def __init__(self, frame_pool, mi_list, var_list=None):
        """run the common init routine to create and register futures, generate the UUID"""
        self._common_init(frame_pool, mi_list)

        #Init. the list of followers as empty.
        self.updated_variables = []

        #Finally, set the allow_attachement
        #self.lock_and_set_attachable(True)
        self.allow_attachement = True


        #Register myself
        self.attach_pulpits()

    def set_variables_to_update(self, var_to_follow):
        """Defines the variables that are updated by this control frame"""
        self.updated_variables = var_to_follow

    def allows_followers(self, required_var_list):
        """Check if this frame can follow all of the required_vars. Control frames start with an empty list that is
        updated by the async routine actually manipulating the motors calling the set_variables_to_update"""

        try:
            for var in required_var_list:
                #Check that the current variable has a motor interactor in the oracle frames list of motor interactors
                self.updated_variables.index(var)
        except ValueError:
            #This means the variable is not in the control frames update list
            return False
        else:
            #All of the required_vars are within the scope of this control frame
            return True


    def start_move_position(self, move_to):
        """Launches the asyncronous routine that actually moves the motor position. """
        #Start the oracle frame async routine.
        self.running_future = asyncio.ensure_future(self.run_move_position(move_to), loop=self.frame_pool.loop)

        for mi in self.mi_list:
            self.updated_variables.append(mi.motor_variables.position)
            self.updated_variables.append(mi.motor_variables.motor_moving)
            self.updated_variables.append(mi.motor_variables.error_flag)
            self.updated_variables.append(mi.motor_variables.error_register)
            self.updated_variables.append(mi.motor_variables.hMT_leadlag_count)
            self.updated_variables.append(mi.motor_variables.hMT_actual_velocity)
        return self.running_future


    @FrameObject.add_pulpit_control_flow
    @FrameObject.handle_communication_errors
    @FrameObject.update_orphaned_followers_afterwards
    async def run_move_position(self, move_to): #Need to add variables to update
        """Run the absolute move routine for a single motor interactor. This routine will check the motor_moving flag util it is set back to zero. This blocks pulpit until complete"""
        debug('run_move_position: starting')
        t0 = time.time()
        mi = self.mi_list[0]

        status = await mi.check_status_and_errors(self.frame_uuid)

        print("Fast_hMT_status: ", status)

        #Execute the move command for this motor
        print("Moving motor interactor '{}' to '{}'".format(mi, move_to))
        await mi.absolute_move(move_to)

        #Poll the motor to find when it stops moving
        while True:
            status = await mi.check_status_and_errors(self.frame_uuid)
            print("Motor status: ", status)

            if status['motor_moving'] is False:
                break

        print("   done in {}s".format(time.time() - t0))


    @FrameObject.add_pulpit_control_flow
    @FrameObject.repeat_until_complete
    @FrameObject.handle_communication_errors
    @FrameObject.handle_motor_config_error
    @FrameObject.update_orphaned_followers_afterwards
    async def run_move_to_indexed_position(self, move_to_index):
        """This will move to an indexed position for my kinematic switching setup"""
        debug('run_move_to_indexed_position: starting')
        t0=time.time()

        cam_mi = self.mi_list[0]
        disc_mi = self.mi_list[1]

        #Do a read on each motor to make sure it is still alive - may not be necessary.
        print("calling fast_hMT status on each motor to check if alive")
        for mi in self.mi_list:
            status = await mi.check_status_and_errors(self.frame_uuid)

        print(" Elapsed time {} seconds".format(time.time()-t0))

        #Start by moving the cam out
        await cam_mi.absolute_move_and_wait(12800, frame_uuid=self.frame_uuid, also_fast_update=[disc_mi])
        print(" Elapsed time {} seconds".format(time.time() - t0))

        #Rotate the disc to the correct index
        await disc_mi.absolute_move_and_wait(25600 * move_to_index, frame_uuid=self.frame_uuid, also_fast_update=[cam_mi])
        print(" Elapsed time {} seconds".format(time.time() - t0))

        # Move the cam back to the locked position
        await cam_mi.absolute_move_and_wait(0, frame_uuid=self.frame_uuid, also_fast_update=[disc_mi])
        print(" Elapsed time {} seconds".format(time.time() - t0))


    @FrameObject.add_pulpit_control_flow
    @FrameObject.repeat_until_complete
    @FrameObject.handle_communication_errors
    @FrameObject.handle_motor_config_error
    @FrameObject.update_orphaned_followers_afterwards
    async def run_get_indexed_position(self):
        """This is a control frame that returns the indexed position of the kinematic switching setup. This is a
        control frame because we want exclusive control of the motor interactors to make sure things are not actually
        moving during the measurement"""
        debug('run_get_index_position: starting')
        t0=time.time()

        cam_mi = self.mi_list[0]
        disc_mi = self.mi_list[1]

        #Do a read to get the motor positions
        cam_status = await cam_mi.check_status_and_errors(self.frame_uuid)
        disc_status = await disc_mi.check_status_and_errors(self.frame_uuid)

        #Position right now is just a simple function
        self.return_result = int( disc_status['position'] / 25600)

