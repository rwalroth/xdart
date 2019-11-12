from mServer.frame_objects import *

from mServer.OracleFrame import *
from mServer.ControlFrame import *
from mServer.PulpitObject import *

import asyncio
import uuid
import time


class FramePool():
    """Create and hold references to all active Frame objects. While control frames are always for a specific action,
    the creation of an oracle frame is only required when nothing is available in the current pool. Thus, it is
    managed here"""

    def __init__(self, loop, mi_list):

        # This is a lock used to prevent any funny business when looking through the list of avialable frames
        # for one that can attach followers. I'm not actually sure this is necessary while we use asyncio
        # (Interestingly asyncio.Lock is not threadsafe - which is OK since we are using asyncio's framework)
        self.attachable_lock = asyncio.Lock()

        #This holds all of the active lists. Make sure to lock when accessing. Be careful not to deadlock!
        self.frame_list = []

        #hold a list of all the motor interactors accessible by this framepool
        self.mi_list = mi_list

        #Hold onto the event loop in which to register everything.
        self.loop = loop

        info('FramePool initialized')


    def find_attachable_frame(self, follower_vars):
        """Search the FramePool for anyone queued up that could provide the information for the followers. If no
        follower exists, create an oracle frame for all motor interactors specified by the follower_vars. Note: This
        will be a linked oracle frame if multiple mi's exist. The frame is returned."""

        print('starting cleanup')
        # Start with some house cleaning.
        self.cleanup_frame_list()

        print('done with cleanup')
        # Make sure we have exclusive access to the attachable list
        #       with (yield from self.attachable_lock):

        # Create an iterator that looks for frames in the frame_list that allow all of the followers
        filtered_frames = filter(lambda x: x.flag_finished is False and x.allows_followers(follower_vars) is True and x.allow_attachement is True, self.frame_list)

        print(filtered_frames)
        # Try to attach to the frame
        try:
            attachable_frame = next(filtered_frames)
            # return the frame_uuid back to the caller
        except StopIteration:  # No FrameObject found that will give the follower the necessary information.
            # So we were not sucessful in attaching followers. Lets Create an oracle frame
            print('creating oracle frame')
            oracle_frame = OracleFrame(frame_pool=self, var_list=follower_vars)
            print(' done creating oracle frame')
            return oracle_frame
        else:  # Alright, we have an attachable_frame. attach followers and return
            attachable_frame.attach_followers(follower_vars)
            return attachable_frame

    def cleanup_frame_list(self):
        """Remove all frames from the frame_list that have flag_delete set to True. frame_list is locked."""
        #This is a bit crude right now and it does require that I actively set FrameObjects to be deleted
#        with (yield from self.attachable_lock):
        self.frame_list = [ frame for frame in self.frame_list if frame.flag_delete is False ]


    def generate_frame_uuid(self):
        """generate unique frame IDs. This is realtively easy to do since all ID's for all motors are generated
         by a s ingle instance of FramePool. This is an 8-digit hexadecimal number which gives us 4,294,967,296 values before
         the sequence could repeat. Since each command takes ~10ms at least, it would take roughly 500 days for something to happen....
         Actually, nothing would happen because commands that old would be taken care of by the garbage collector long long long before
         that happened. """

        frame_uuid = uuid.uuid4().hex[:8].upper()
        return frame_uuid


    def get_attachable_variables(self, mi_list=None, include_hidden_variables = True):
        """Return a list of variables that can be set / get (followed). The return object is a dictionary with the
        motor interactor as the key with a dictionary of motor variaibles. include_hidden_variables is true by default"""
        ret_dict = {}

        if mi_list is None:
            mi_list = self.mi_list

        for mi in mi_list:
            ret_dict[mi] = mi.motor_variables.get_motor_variables(include_hidden_variables=include_hidden_variables)

        return ret_dict



    async def setup_background_tasks(self):
        """Start the asynchronous background tasks that concern the frame pool"""
        info('FramePool background tasks started')

        #Start frame_list cleanup routine
        asyncio.ensure_future(self.cleanup_old_frames(), loop=self.loop)

    async def cleanup_old_frames(self, cleanup_interal = 5, remove_frames_older_than = 300):
        """Run garbage collection in the background while """
        while True:
            #Wait for a little bit
            await asyncio.sleep(cleanup_interal, loop=self.loop)

            start_time = time.time()
            #Delete elements flagged for
            self.frame_list = [frame for frame in self.frame_list if frame.flag_delete is True]

            #Delete elements that are too old
            current_time = time.time()
            self.frame_list = [frame for frame in self.frame_list if frame.flag_finished is True and (current_time - frame.time_created) > remove_frames_older_than]

            print("cleanup_old_frames: it took {} seconds to cleanup".format(time.time() - start_time))


