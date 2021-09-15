try:
    from asyncio import create_task

    create_task = create_task
except:
    from asyncio import ensure_future

    create_task = ensure_future

try:
    from asyncio import get_running_loop

    get_running_loop = get_running_loop
except:
    from asyncio import get_event_loop

    get_running_loop = get_event_loop

