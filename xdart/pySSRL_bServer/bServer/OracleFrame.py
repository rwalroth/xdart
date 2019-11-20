
import asyncio


class OracleFrame(FrameObject):

    def __init__(self, frame_pool, var_list):
        """Create the oracle frame to follow motor interactors that cover all the variables in var_list. Do not
        actually attach the followers here since that will make it awkward to return the futures each var will
        actually track"""
        #Create the mi_list based off the unique mi values in var_list
        self.mi_list = self.get_motor_interactors_from_var_list(var_list)

        #print("before common init")
        #run the common init routine to create and register futures and generate the UUID
        (self._common_init(frame_pool, self.mi_list))

        #Finally, set us to be attachable for followers. I probably could have done this earlier.
        #self.lock_and_set_attachable(True)
        self.allow_attachement = True

        #self.attach_followers(var_list=var_list)


        #add frame to pulpits required for var_list. Reserves our place in the queue
        self.attach_pulpits()

        #Start the async oracle meaurement
 #       self.start()

    def start(self):
        """Launches the asyncronous routine that actually updates the motor position. """
        #Start the oracle frame async routine.
        self.running_future = asyncio.ensure_future(self.run_oracle_frame(), loop=self.frame_pool.loop)




    def get_motor_interactors_from_var_list(self, var_list):
        """get all of the unique motor interactors from a list of variables."""

        #Pretty simple trick. Get all of the motor_interactors in a list, convert it to a set (which removes duplicates) and then convert that back to a list.
        mi_list = list(set([motor_var.mi for motor_var in var_list]))

        return mi_list


    def allows_followers(self, required_var_list):
        """Check if this frame can follow all of the required_vars. Oracle frames always allow followers if they are in the motor interactor associated with this frame."""
        try:
            for var in required_var_list:
                #Check that the current variable has a motor interactor in the oracle frames list of motor interactors
                self.mi_list.index(var.mi)
        except ValueError:
            #This means the variable was associated with a motor interactor not in the oracle frames MI list
            return False

        else:
            #All of the required_vars are within the scope of this oracle frame
            return True





    async def run_oracle_frame(self):
        """Lets implement the actual oracle frame. It runs asyncronously and is launched by the http handler. First, we
        wait on the start futures. Second, we turn off the ability to attach. Thrid, we loop through all of the motor
        interactors and execute updates for any routines that have followers. Finally, we set the end futures and end
        the function."""


        #Add a context manager to handle errors


        #wait on the start futures to be set by the pulpits



        print("Starting run_oracle_frame", self)
        for (pulpit_obj, future) in self.start_future.items():
            print("run_oracle_frame checking future. Future: {}  Pulpit: {}".format(future, pulpit_obj))
            if future.done() is False:
                print('  waiting on Future')
                await future
            else:
                print('  continuing')

        t0 = time.time()
        print("stopping attachement")
        #Stop attachement
        self.allow_attachement = False

        print("  mi_list: ", self.mi_list)
        for mi in self.mi_list:

            var_dict = mi.motor_variables.get_motor_variables()

            #print(var_dict)

            for (var_name, motor_var) in var_dict.items(): #This is a little clunky but will work

                #print("Looking at {}: {}".format(var_name, motor_var))
                #Technically, we could just run the update routine... but lets check so we can be sure what we are updating...

                num_followers = motor_var.get_followers(self.frame_uuid)
                #print(" num_followers: ", num_followers)
                if num_followers is not None:
                    print("Updating followers of variable '{}'".format(var_name))
                    await motor_var.read_value(self.frame_uuid)
                    print("  updating {}: {}s".format(motor_var.name, time.time()-t0))
                    #motor_var.update_followers(oracle_frame.frame_uuid)



        #print("setting end futures")
        #Set the end routines
        for (pulpit_obj, future) in self.end_future.items():
            print("run_oracle_frame setting end. Future: {}  Pulpit: {}".format(future, pulpit_obj))
            future.set_result("  finished {}".format(time.time()))
            print("  end future set ", future)

        self.flag_finished = True
