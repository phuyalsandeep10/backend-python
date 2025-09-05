import socketio
from socketio import AsyncRedisManager
from socketio.redis_manager import redis

from src.config.redis.redis_listener import  redis_listener
from src.config.settings import settings
from src.websocket.chat_namespaces.agent_chat_namespace import AgentChatNamespace
from src.websocket.chat_namespaces.customer_chat_namespace import CustomerChatNamespace
from src.websocket.namespace.ticket.sla_namespace import TicketSLANameSpace
from src.websocket.namespace.ticket.ticket_namespace import TicketNameSpace

redis_url = settings.REDIS_URL
mgr = AsyncRedisManager(redis_url)


from src.app import app

# Create the Socket.IO Async server (ASGI mode)

sio = socketio.AsyncServer(
        async_mode="asgi",
        cors_allowed_origins="*",
        client_manager=mgr,
    )


# ASGIApp wraps Socket.IO and FastAPI into one ASGI application
try:
    socket_app = socketio.ASGIApp(
        socketio_server=sio, other_asgi_app=app, socketio_path="/ws/sockets/socket.io"
    )
    print("✅ ASGI app created successfully")
except Exception as e:
    print(f"⚠️ Error creating ASGI app: {e}")
    import traceback
    traceback.print_exc()
    # Fallback to basic ASGI app
    socket_app = app


sio.register_namespace(CustomerChatNamespace())
sio.register_namespace(AgentChatNamespace())



# Global task reference to prevent garbage collection
redis_listener_task = None


# Wire redis subscriber at app startup to avoid circular imports in chat_handler
@app.on_event("startup")
async def start_ws_redis_listener():
    import asyncio

    global redis_listener_task

    print("🚀 Starting WebSocket Redis listener...")
    try:
        # Create task with proper error handling
        redis_listener_task = asyncio.create_task(redis_listener(sio))

        # Add error callback to catch silent failures
        def task_done_callback(task):
            if task.exception():
                print(f"❌ Redis listener task failed: {task.exception()}")
                import traceback

                traceback.print_exception(
                    type(task.exception()), task.exception(), task.exception().__traceback__
                )
            else:
                print("ℹ️ Redis listener task completed normally")

        redis_listener_task.add_done_callback(task_done_callback)
        print("✅ WebSocket Redis listener task created")
    except Exception as e:
        print(f"❌ Failed to start Redis listener: {e}")
        import traceback
        traceback.print_exc()


@app.on_event("shutdown")
async def stop_ws_redis_listener():
    import asyncio

    global redis_listener_task
    if redis_listener_task and not redis_listener_task.done():
        print("🛑 Stopping Redis listener task...")
        try:
            redis_listener_task.cancel()
            await redis_listener_task
        except asyncio.CancelledError:
            print("✅ Redis listener task cancelled")
        except Exception as e:
            print(f"⚠️ Error stopping Redis listener: {e}")


ticket_ns = TicketNameSpace()
ticket_sla_ns = TicketSLANameSpace()
sio.register_namespace(ticket_ns)
sio.register_namespace(ticket_sla_ns)
