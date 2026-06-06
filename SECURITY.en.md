# Security Policy

> 繁體中文版本：[SECURITY.md](SECURITY.md)

## Reporting a Vulnerability

If you find a security vulnerability in usage, **please do not open a public Issue.** Report it privately instead:

📧 **aqua5230@gmail.com**

Please include where you can:

- The affected version (or commit)
- Steps to reproduce, or a proof of concept
- Your assessment of the impact

This is a single-maintainer project; I'll do my best to respond and address reports within a reasonable timeframe, and will credit you in the release notes once a fix ships (unless you prefer to stay anonymous).

## Supported Versions

usage ships on a rolling basis; security fixes target the **latest release only**. Please confirm you're on the [latest release](https://github.com/aqua5230/usage/releases/latest) before reporting.

## Security Design

usage **never calls any Anthropic / OpenAI network API.** Every number comes from files already on your local disk (the status file Claude Code writes, and Codex's session logs). It does not upload, track, or phone home with your usage data — that's a core design principle of the project.
