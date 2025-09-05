AGENT_NOTIFICATION_CHANNEL = "chat-agent-notification-channel"
MESSAGE_CHANNEL = "chat-message-channel"
TYPING_CHANNEL = "chat-typing-channel"
TYPING_STOP_CHANNEL = "chat-typing-stop-channel"
MESSAGE_SEEN_CHANNEL = "chat-message-seen-channel"
CUSTOMER_NOTIFICATION_CHANNEL = "chat-customer-notification-channel"
AGENT_AVAILABILITY_CHANNEL = "chat-agent-availability-channel"

CONVERSATION_UNRESOLVED_CHANNEL = "chat-conversation-unresolved-channel"
CUSTOMER_JOIN_CONVERSATION = "chat-customer-join-conversation-channel"
AGENT_JOIN_CONVERSATION = "chat-agent-join-conversation-channel"
CUSTOMER_LAND_WEBSITE = "chat-customer-land-website-channel"
AGENT_ONLINE_CHANNEL = "chat-agent-online-channel"
CUSTOMER_LEAVE_CONVERSATION='chat-customer-leave-channel'
AGENT_LEAVE_CONVERSATION='chat-agent-leave-channel'
AGENT_OFFLINE_CHANNEL = 'chat-agent-offline-channel'
CUSTOMER_OFFLINE_CHANNEL = 'chat-customer-offline-channel'

def is_chat_channel(channel_name):
    return channel_name.startswith("chat-")