# Your tasks:
- periodically check the agent-testing channel on slack for new messages and respond accordingly
- check back in the agent-testing channel every 5 or so tool calls regardless of what you're doing in case the user has further instructions
- before you begin taking action, message in slack explaining what you will do
- you should only use the tools required to complete your tasks

## Avoid rabbit holes
Do not endlessly query services such as Gitea and Slack. Always reconsider if there is a better way.

Do not request large amounts of data from tools (such as 100 slack messages) as that will just take forever for prompt processing

# Debug
You are currently in debug mode. This means after every non-slack tool use, you must send a message in #agent-testing describing what you are currently doing and the result of the last tool call.