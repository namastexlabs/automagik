# Agent Communication System

## 🎯 **Overview**

The new Agent Communication System enables asynchronous inter-agent communication through Claude sessions with proper tmux session management and WhatsApp notifications.

## 🚀 **Key Features**

### ✅ **Fixed Issues**
- **Asynchronous Communication**: Agents can send messages and continue working
- **Session Integration**: Messages are delivered directly to Claude sessions
- **Proper Monitoring**: All agents run in tmux sessions and are visible to monitoring
- **WhatsApp Notifications**: Real-time updates on communication events
- **Message Tracking**: Unique message IDs and status tracking

### 🔧 **Architecture**

```
┌─────────────┐    agent_communicate.sh    ┌─────────────┐
│   Agent A   │ ────────────────────────► │   Agent B   │
│ (Claude +   │                          │ (Claude +   │
│  TMux)      │ ◄──────────────────────── │  TMux)      │
└─────────────┘    agent_communicate.sh    └─────────────┘
       │                                         │
       ▼                                         ▼
┌─────────────────────────────────────────────────────────┐
│              WhatsApp Notifications                    │
│          + Message Tracking System                     │
└─────────────────────────────────────────────────────────┘
```

## 📋 **Usage Examples**

### **For Orchestrator (Alpha)**
```bash
# Start an agent with task
./agent-scripts/run_beta.sh "Implement user authentication"

# Send message to another agent
./agent_communicate.sh alpha beta "Status update on authentication?"

# Check responses
./agent_communicate.sh check alpha

# Monitor all agents
./monitor_agents.sh
```

### **For Humans**
```bash
# Continue any agent session
RESUME_SESSION=<session_id> ./agent-scripts/run_<agent>.sh

# Continue with new input
RESUME_SESSION=<session_id> ./agent-scripts/run_beta.sh "Focus on error handling"

# Watch agent work in real-time
tmux attach -t agent-alpha

# Check communication logs
ls -la .claude/scripts/communications/
```

## 🔄 **Communication Flow**

### **1. Sending Messages**
```bash
./agent_communicate.sh alpha beta "Please implement user authentication"
```

**What happens:**
1. ✅ **Validation**: Check if target agent (beta) is active
2. 📝 **Message Creation**: Generate unique message ID and log
3. 📨 **Delivery**: Inject message into beta's Claude session via tmux
4. 📱 **Notification**: Send WhatsApp notification with status
5. ✅ **Response**: Return immediately with "Message sent successfully"

### **2. Receiving Messages**
When an agent receives a message, Claude gets:
```
[INTER-AGENT MESSAGE]
From: 🎯 Alpha Orchestrator
Message ID: msg_1735565400_alpha_to_beta

Please implement user authentication

Please respond using the agent_communicate_reply tool with message_id: msg_1735565400_alpha_to_beta
After responding, continue with your current task.
```

### **3. Replying to Messages**
```bash
./agent_communicate_reply.sh msg_1735565400_alpha_to_beta beta "Authentication implemented successfully"
```

**What happens:**
1. 🔍 **Find Original**: Locate original message file
2. 📤 **Send Reply**: Use communication system to reply to sender
3. ✅ **Mark Complete**: Update message status to "replied"
4. 📱 **Notify**: Send WhatsApp confirmation

## 🛠️ **Tool Reference**

### **agent_communicate.sh**

#### **Send Message**
```bash
./agent_communicate.sh <sender> <target> <message>
```
- **sender**: alpha, beta, delta, epsilon, gamma
- **target**: alpha, beta, delta, epsilon, gamma  
- **message**: Text message to send

#### **Reply to Message**
```bash
./agent_communicate.sh reply <message_id> <sender> <reply_message>
```

#### **Check Messages**
```bash
./agent_communicate.sh check <agent>
```

#### **List Active Agents**
```bash
./agent_communicate.sh list
```

### **agent_communicate_reply.sh**
```bash
./agent_communicate_reply.sh <message_id> <sender_agent> <reply_message>
```

## 📁 **File Structure**

```
.claude/scripts/
├── agent_communicate.sh          # Main communication system
├── agent_communicate_reply.sh    # Reply tool for agents
├── communications/               # Message storage
│   ├── alpha_incoming_msg_*.json # Incoming messages for alpha
│   ├── beta_incoming_msg_*.json  # Incoming messages for beta
│   └── ...
├── logs/                        # Communication logs
│   ├── agent_comm_msg_*.log     # Communication attempts
│   └── ...
└── sessions/                    # Session tracking
    ├── alpha_session.txt        # Claude session IDs
    ├── alpha_tmux.txt          # TMux session names
    └── ...
```

## 🔍 **Message Format**

### **Message File Structure**
```json
{
    "message_id": "msg_1735565400_alpha_to_beta",
    "from": "alpha",
    "to": "beta", 
    "message": "Please implement user authentication",
    "timestamp": "2025-05-30T07:30:00Z",
    "status": "delivered"
}
```

### **Status Values**
- `pending`: Message created but not delivered
- `delivered`: Message delivered to target agent
- `replied`: Target agent has replied

## 📱 **WhatsApp Notifications**

### **Message Sent**
```
💬 Agent Communication

👤 From: 🎯 Alpha Orchestrator
👤 To: 🔨 Beta Core Builder
🆔 ID: msg_1735565400_alpha_to_beta
⏰ Time: 07:30:00

📝 Message:
> Please implement user authentication

🔄 Delivering message...
```

### **Message Delivered**
```
✅ Message Delivered

👤 alpha → beta
🆔 ID: msg_1735565400_alpha_to_beta
📨 Status: DELIVERED
🖥️  Session: agent-beta

⏳ Waiting for beta to respond...
```

### **Message Failed**
```
❌ Message Delivery Failed

👤 alpha → beta
🆔 ID: msg_1735565400_alpha_to_beta
🚫 Error: Target agent not active

💡 To start target agent:
`./agent-scripts/run_beta.sh "Please implement user authentication"`
```

## ⚡ **Performance Features**

### **Asynchronous Processing**
- Messages return immediately with confirmation
- No blocking waits for responses
- Agents can continue working while waiting for replies

### **Session Management**
- All agents run in tmux sessions
- Proper Claude session tracking
- Automatic session validation

### **Monitoring Integration**
- All communications visible in `monitor_agents.sh`
- Real-time tmux session status
- WhatsApp notifications for all events

## 🔧 **Troubleshooting**

### **Agent Not Responding**
```bash
# Check if agent is active
./agent_communicate.sh list

# Check for pending messages
./agent_communicate.sh check beta

# Restart agent if needed
./agent-scripts/run_beta.sh "Continue previous task"
```

### **Message Not Delivered**
```bash
# Check communication logs
ls -la .claude/scripts/logs/agent_comm_*.log

# Check message files
ls -la .claude/scripts/communications/

# Verify tmux sessions
tmux list-sessions | grep agent-
```

### **Session Issues**
```bash
# Check session files
ls -la .claude/scripts/sessions/

# Force new session if needed
FORCE_NEW_SESSION=true ./agent-scripts/run_beta.sh "Fresh start"
```

## 🎯 **Best Practices**

### **For Agent Communication**
1. ✅ **Always check status** before sending messages
2. ✅ **Use descriptive messages** for better context
3. ✅ **Include task context** in communication
4. ✅ **Reply promptly** to maintain workflow

### **For Session Management**
1. ✅ **Monitor agent status** regularly
2. ✅ **Use tmux sessions** for all agent work
3. ✅ **Keep session IDs** for continuity
4. ✅ **Force new sessions** when needed

### **For Debugging**
1. ✅ **Check logs first** for communication issues
2. ✅ **Verify tmux sessions** are active
3. ✅ **Use WhatsApp notifications** for real-time updates
4. ✅ **Test with simple messages** before complex tasks

---

**🎉 Now all agents can communicate asynchronously while maintaining proper tmux session management and monitoring capabilities!** 