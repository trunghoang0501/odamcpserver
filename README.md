# ODA MCP Server

## Configuration

To configure the MCP server, add the following configuration to your MCP config file:

```json
{
  "mcpServers": {
    "Study": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/trunghoang0501/odamcpserver.git",
        "mcp-server"
      ]
    }
  }
}
```

## Usage

Once configured, you can interact with the MCP server using the appropriate client libraries.

## Set up

Please add your .env file to the root directory of the project with open AI API key.
