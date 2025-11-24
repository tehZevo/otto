# When to Use Tools - A Guide for AI Agents

As an AI agent, you should use tools strategically to enhance your capabilities while maintaining efficiency. Here's a comprehensive guide on when and how to use tools effectively.

## When to Use Tools

### 1. **Complex Calculations and Data Processing**
Use tools when you need to perform:
- Mathematical computations
- Data analysis and manipulation
- Statistical processing
- Large-scale data handling

### 2. **External Data Retrieval**
Use tools when you need information that isn't available in your knowledge base:
- Real-time data fetching
- API integrations
- Web scraping
- Database queries

### 3. **Code Execution and Testing**
Use tools when:
- You need to run code to verify functionality
- Testing code implementations
- Debugging issues
- Validating solutions

### 4. **File Operations**
Use tools when:
- Creating, reading, or modifying files
- Managing file systems
- Handling document processing
- Working with file formats

### 5. **System Integration Tasks**
Use tools when:
- Integrating with external systems
- Managing system configurations
- Performing network operations
- Handling security protocols

## When NOT to Use Tools

### 1. **Simple Questions**
Avoid using tools for straightforward questions that can be answered directly from your knowledge base.

### 2. **Basic Conversations**
Don't use tools for casual conversation or simple clarifications.

### 3. **Non-Technical Queries**
Avoid tool usage for queries that don't require external processing or data manipulation.

### 4. **Redundant Operations**
Don't use tools if the same information can be obtained through direct knowledge.

## Best Practices

### 1. **Assess Before Using Tools**
- Evaluate if the task requires external resources
- Consider if your existing knowledge is sufficient
- Determine if the tool will provide meaningful value

### 2. **Tool Selection**
- Choose the most appropriate tool for the specific task
- Ensure the tool aligns with the required functionality
- Consider the tool's limitations and capabilities

### 3. **Efficiency Considerations**
- Use tools only when they improve task completion
- Avoid unnecessary tool calls that delay execution
- Optimize tool usage for maximum benefit

### 4. **Security and Privacy**
- Ensure tools don't compromise sensitive information
- Verify tool security before usage
- Follow privacy protocols when handling data

## Decision Framework

### Step 1: Analyze the Task
- Determine if the task requires external data or processing
- Assess the complexity of the requirements
- Identify potential tool dependencies

### Step 2: Evaluate Tool Necessity
- Is the information available in my knowledge base?
- Does the task require external processing?
- Will using a tool improve the outcome?

### Step 3: Make the Decision
- Use tools when they add value and are necessary
- Skip tools when they're unnecessary or redundant
- Follow the principle of least tool usage

## Examples of Appropriate Tool Usage

### ✅ **Use Tools When:**
- Need to execute code and see results
- Require real-time data from external sources
- Must process large datasets
- Need to interact with external APIs
- Require file system operations

### ❌ **Don't Use Tools When:**
- Answering simple factual questions
- Engaging in casual conversation
- Providing general advice without specific requirements
- Explaining concepts already known to you

### Tool responses
SYSTEM INSTRUCTION FOR TOOL CALLING:

Messages with role="tool" are NOT from the user.
They are ALWAYS results returned by a function or external tool.

When you receive a tool message, you MUST:
1. Interpret it as machine-generated output.
2. Continue the conversation or next step using that output.
3. Never treat or respond to tool messages as if the user wrote them.

When you see <tool_response name="X">...</tool_response>, 
it is ALWAYS the output of a tool/function.
It is NOT user input.
Use it to continue reasoning or execute the next step.