# Repository-Wide Instructions for Feed of Feeds (FoF)

## Platform Compatibility Requirements

This project **must work on both Termux and Ubuntu** environments. When making
changes, always consider compatibility with both platforms:

### Target Platforms

- **Ubuntu**: Standard Linux desktop/server environment
- **Termux**: Android terminal emulator with Linux userland

## Platform-Specific Considerations

### Package Installation

- **Ubuntu**: Use `pipx` for user installations due to PEP 668 restrictions
- **Termux**: Use `pkg` for system packages and `pip` for Python packages
- Always test installation methods on both platforms
- Consider using `pip install --user` as a fallback option

### File System Considerations

- **Ubuntu**: Standard Linux filesystem hierarchy (`~/.config/`, `/tmp/`, etc.)
- **Termux**: Android filesystem with different permissions and paths
- Use Python's `os.path`, `pathlib`, or `tempfile` modules for cross-platform paths
- Always handle permission errors gracefully
- Test file operations in both restricted and standard environments

### Terminal and Curses Support

- **Ubuntu**: Full terminal capabilities with standard curses
- **Termux**: May have terminal limitations or different key mappings
- Ensure the interactive article reader works in both environments
- Provide fallback options if curses features are limited
- Test keyboard input handling across platforms

### Network and Connectivity

- Both platforms should handle RSS/Atom feed fetching equally
- Consider network restrictions or proxy settings that might differ
- Implement proper error handling for network failures

## Development Guidelines

### Testing Strategy

- Test on both Ubuntu and Termux when possible
- Use containers or virtual environments to simulate different platform conditions
- Pay attention to permission errors, path issues, and terminal capabilities,
  but keep in mind that
  termux/termux-docker is not a perfect simulation of a real termux environment.
- Verify CLI functionality and interactive features work on both platforms

### Code Patterns

- Use cross-platform Python libraries and patterns
- Avoid hardcoded paths or platform-specific assumptions
- Handle platform differences gracefully with try/catch blocks
- Document any known platform-specific behaviors or limitations

### Installation Instructions

- Provide clear installation steps for both platforms
- Include troubleshooting for common platform-specific issues
- Test all documented installation methods
- Consider package manager differences (apt vs pkg)

## Error Handling

- Gracefully handle platform-specific errors (permissions, missing features)
- Provide helpful error messages that guide users to platform-specific solutions
- Log platform information when debugging issues
- Test error scenarios on both platforms

## Configuration

- Ensure config file paths work on both platforms
- Handle different home directory structures
- Test configuration persistence across platform restarts
- Consider platform-specific default configurations if needed

When implementing features or fixing bugs, always verify that changes work
correctly on both Termux and Ubuntu environments.
