import asyncio, sys
sys.path.append('C:\\Users\\Public\\repos\\xdart')

from xdart.modules.pySSRL_bServer.bServer.BL_Error import *

class PulpitObject():
    """The pulpit object handles the first in, first out queueing of frame objects. The concept is simple enoguh - only
    one frame can be speaking at the pulpit at any given time. In the case of the Lexium MDrive Motors, each motor interactor
    has a 'pulpit' object. For a controller that controls mutiple motors, each motor would have its own pulpit object,
    meaning there would be multiple pulpits per motor interactor (e.g. the galil's)"""
    def __init__(self, loop):

        self.loop = loop

        self.frame_queue = asyncio.Queue(loop=self.loop)

        self.executing_frame = None

        #Start the frame scheduler.
        self.consumer_future = asyncio.ensure_future(self.schedule_frames(), loop=self.loop)

    def add_frame(self, new_frame):
        #print("adding frame")
        self.frame_queue.put_nowait(new_frame)
        #print("    done adding frame")

    async def schedule_frames(self):
        """Responsible for setting the result of the 'start' (for this specific object) and waiting on the 'end' future
        associated with this object. This effectively coordinates puts one frame on the pulpit at a time."""
        while True:
            print('starting wait in schedule_frames')
            self.executing_frame = await self.frame_queue.get()

            if self.executing_frame is None: #Just in case we want to stop the PulpitObject
                print("Got null frame. Stopping Pulpit")
                break

            print("pulpit {} setting 'start' future {} in frame {}".format(self, self.executing_frame.start_future, self.executing_frame))
            start_future = self.executing_frame.start_future[self]

            print("  assigned start_future= ", start_future)

            #set the result of the start future. This will start the routine associated with this frame
            print("schedule_frames: ** Set to done: ", start_future.set_result("Start!"))

            #Wait for the frame to finish before starting the next
            end_future = self.executing_frame.end_future[self]
            print("Waiting for end_future to be set to end:", end_future)

            res_end = await end_future

            print("  pulpit {} 'end' future in frame {} completed".format(self, self.executing_frame))



    def number_waiting(self):

        return self.frame_queue.qsize()

