import socket
import time
import types
import sys
import yaml
import copy
import logging
from logging import info, warning, critical, debug
import asyncio
from aiohttp import web
import functools
from time import gmtime, strftime

sys.path.append('C:\\Users\\Public\\repos\\xdart')
from xdart.modules.pySSRL_bServer.bServer.bl_communication import *
from xdart.modules.pySSRL_bServer.bServer.bl_command import *
from xdart.modules.pySSRL_bServer.bServer.BL_Error import *
from xdart.modules.pySSRL_bServer.bServer.bl_interaction import *


async def handleGET_motor_position(request):
    """Quick routine to test reading the motor position from SPEC"""
    t0 = time.time()

    motor_name = request.match_info.get('motor_name', None)
    print("getting motor variable '{}' ".format(motor_name))

    bi = request.app['bi']

    comm = bi.beamline

    cmd_text = "?mp {}".format(motor_name)

    cmd = BLCommand(comm, cmd_text, needsResponse=True)

    await cmd.execute()

    print(cmd)

    response = cmd.typecastResponse([float])
    print("Response: '{}'".format(response))
    print("\n\n\nRequest took: {}s\n\n".format(time.time() - t0))

    #convertedResults = {'hi': 'there', 'position': response}
    convertedResults = {'position': response}
    return web.json_response(convertedResults)


async def handleGET_tt(request):
    """Quick routine to test reading the motor position from SPEC"""
    t0 = time.time()
    print("starting tt")
    bi = request.app['bi']

    comm = bi.beamline

    cmd1 = BLCommand(comm, "!rqc", needsResponse=True)
    cmd2 = BLCommand(comm, "!cmd umv rail3_y -5", needsResponse=True)
    cmd3 = BLCommand(comm, "!rlc", needsResponse=True)

    cmd = cmd1 + cmd2 + cmd3
    await cmd.execute()

    #response = cmd.response
    print(cmd)

    print("Response: '{}'".format(cmd))
    print("\n\n\nRequest took: {}s\n\n".format(time.time() - t0))

    convertedResults = {'hi': 'there', 'position': cmd}
    return web.json_response(convertedResults)


async def handleGET_test(request):
    """Quick routine to test reading the motor position from SPEC"""
    t0 = time.time()
    print("starting test")
    bi = request.app['bi']

    try:

        await bi.sis.get_remote_control()
        response = await bi.sis.are_we_in_control()
#        starting_at = await bi.sis.get_console_output_buffer(get_buffer_index=True)
#        print("Starting index: {}".format(starting_at))
#        await bi.sis.execute_command("ct 0.3")

#        #await asyncio.sleep(2)
#        response = await bi.sis.get_console_output_buffer(N=starting_at, return_after=True)
#        print("What happened:\n\n", response)
#        answer = await bi.sis.retrieve_result()
#        print("Answer:\n", answer)

        await bi.sis.release_remote_control()

    except:
        print("problem in test: {}".format(sys.exc_info()[0]))
        raise

    print("Response: '{}'".format(response))
    print("\n\n\nRequest took: {}s\n\n".format(time.time() - t0))

    convertedResults = {'hi': 'there', 'data': response}
    return web.json_response(convertedResults)


async def handleGET_directSISinteraction(request):
    """Quick routine to test reading the motor position from SPEC"""
    t0 = time.time()
    print("starting direct SPEC Infoserver interaction")
    bi = request.app['bi']


    command_name = request.match_info.get('command_name', None)
    command_params = {}
    #Get the parameters passed as part of the GET request
    query = request.query
    print("Found arguments: (Key-> Val)\n")

    for (key, val) in query.items():
        print("   '{}'->'{}'".format(key, val))
        if val == "True" or val == "true":
            command_params[key] = True
        elif val == "False" or val == "false":
            command_params[key] = False
        elif val == "None" or val == "none":
            command_params[key] = None
        else:
            command_params[key] = val

    response = {}
    try:

        sis_command = getattr(bi.sis, command_name, None)
        print("sis_command object: ", sis_command)

        response['help'] = sis_command.__doc__
        response['data'] = await sis_command(**command_params)
        pass
    except:
        print("problem in test: {}".format(sys.exc_info()[0]))
        response = {'error': sys.exc_info()[0]}

#        raise

    print("Response: '{}'".format(response))
    print("\n\n\nRequest took: {}s\n\n".format(time.time() - t0))

    return web.json_response(response)

########################################################################################################################
########################################################################################################################


log_datetime = strftime("%Y-%m-%d_%H_%M_%S", gmtime())
logging.basicConfig(filename='bServerLog__{}.log'.format(log_datetime), level=logging.DEBUG)

#Setup the event loop
loop = asyncio.new_event_loop()
loop.set_debug(True)
asyncio.set_event_loop(loop)


#Initialize the connection to SPEC
temp_bi = BL_Interaction(loop=loop, beamline_name='bl11-3_testConfig')

#Initialize the http web application and register routes
app = web.Application()

app.router.add_get("/motor/{motor_name}/position", handleGET_motor_position)
app.router.add_get("/tt", handleGET_tt)
app.router.add_get("/test", handleGET_test)
app.router.add_get("/SIS/{command_name}", handleGET_directSISinteraction)


#app.router.add_post("/motor/{motor_name}", handlePOST_move_motor)

app['bi'] = temp_bi

web.run_app(app, host='127.0.0.1', port=18085)#, loop=loop)
