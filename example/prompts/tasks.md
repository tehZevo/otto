# Your tasks:
- clone the agent-alice/alice-test repo
- gitea is located at "http://host.docker.internal:3000" (not localhost)
- your gitea username is agent-alice
- send a message on the agent-testing channel in slack describing the contents of the repo
- all work should be done in the /workspace directory
- DO NOT describe what you will do - call tools immediately
- every response MUST include actual tool calls unless your work is complete

## example tool call:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>