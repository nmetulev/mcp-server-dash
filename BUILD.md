# Building a Standalone Executable

This guide explains how to create a standalone Windows executable from the mcp-server-dash using PyInstaller.

## Prerequisites

- Python 3.10 or higher
- All project dependencies installed (`pip install -e .`)

## Quick Build

Run the build script:

```powershell
.\build.ps1
```

This will:
1. Install PyInstaller if needed
2. Clean previous builds
3. Create a standalone executable in `dist\mcp-server-dash.exe`

## Manual Build

If you prefer to build manually:

1. Install PyInstaller:
```powershell
pip install pyinstaller
```

2. Run PyInstaller with the spec file:
```powershell
pyinstaller mcp-server-dash.spec
```

3. The executable will be created in `dist\mcp-server-dash.exe`

## Configuration

The PyInstaller spec file (`mcp-server-dash.spec`) includes:
- All necessary hidden imports for MCP, Dropbox SDK, and dependencies
- Data files for packages that need them
- Single-file executable configuration
- Console mode enabled for stdio communication

## Using the Executable

1. **Set up environment variables:**
   - Create a `.env` file in the same directory as the executable with your `APP_KEY`
   - Or set the `APP_KEY` environment variable

2. **Run the executable:**
   ```powershell
   .\dist\mcp-server-dash.exe
   ```

3. **Configure in Claude Desktop or other MCP clients:**
   Update your MCP client configuration to point to the executable:
   ```json
   {
     "mcpServers": {
       "dash": {
         "command": "C:\\path\\to\\dist\\mcp-server-dash.exe",
         "env": {
           "APP_KEY": "your-app-key-here"
         }
       }
     }
   }
   ```

## Troubleshooting

### Missing Modules
If the executable fails with import errors, you may need to add the missing module to the `hiddenimports` list in `mcp-server-dash.spec`.

### Large File Size
The single-file executable includes Python runtime and all dependencies. Typical size is 30-50 MB. You can reduce size by:
- Using `upx=True` (already enabled in the spec file)
- Excluding unnecessary modules in the spec file

### Antivirus False Positives
Some antivirus software may flag PyInstaller executables. This is a known issue. You may need to:
- Add an exception for the executable
- Use code signing (requires a certificate)

### Keyring Issues
The Windows keyring backend is included, but if you have issues with token storage:
- Make sure the executable runs with appropriate Windows user permissions
- Check that the Windows Credential Manager is accessible

## Advanced Customization

Edit `mcp-server-dash.spec` to customize:
- `console=True/False` - Whether to show a console window
- `onefile=True/False` - Single file vs. directory distribution
- `icon='path/to/icon.ico'` - Add a custom icon
- `hiddenimports` - Add modules that aren't auto-detected
- `excludes` - Exclude unnecessary modules to reduce size
