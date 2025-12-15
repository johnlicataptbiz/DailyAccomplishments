# GitHub Copilot Configuration

This directory contains configuration files for GitHub Copilot and custom agents.

## Files Overview

### copilot-instructions.md
**Primary instruction file for GitHub Copilot**

This is the main instruction file that provides comprehensive guidance including:
- Project overview and structure
- Key integrations (HubSpot, Aloware, Monday.com, Slack, Google Calendar)
- Coding standards and conventions
- Git workflow and verification practices
- Railway deployment verification
- Frontend robustness guidelines
- Communication style and best practices

**When it's used**: Automatically loaded by GitHub Copilot for all interactions in this repository.

### instructions/ActivityChatAgentPrompt.instructions.md
**Workflow-focused instruction template**

Contains verification-first workflow rules including:
- No unverifiable claims policy
- Git discipline (never git add -A, always show outputs)
- Standard workflow (diagnose, change, commit, push, verify)
- Railway deployment verification commands
- Communication style guidelines

**Status**: The key concepts from this file have been **integrated into copilot-instructions.md** (December 15, 2025). This file is retained as a reference for the workflow patterns.

### agents/SuperAgent.agent.md
**Custom agent definition**

This is a GitHub Copilot custom agent that wraps the same workflow rules as ActivityChatAgentPrompt.instructions.md but in a custom agent format (with YAML front matter).

**When it's used**: Can be explicitly invoked as a custom agent when you want to enforce strict verification-first workflow practices.

## Relationship Between Files

```
copilot-instructions.md (PRIMARY - comprehensive)
├── Project context & guidelines
├── Integrations & structure
└── Workflow rules (integrated from ActivityChatAgentPrompt)

ActivityChatAgentPrompt.instructions.md (REFERENCE)
└── Workflow verification patterns

SuperAgent.agent.md (CUSTOM AGENT)
└── Same workflow rules as ActivityChatAgentPrompt, custom agent format
```

## Integration Status

✅ **Complete**: All key workflow concepts from ActivityChatAgentPrompt.instructions.md have been integrated into copilot-instructions.md
- Git workflow discipline
- Verification-first approach  
- Railway deployment verification
- Frontend robustness guidelines
- Communication style
- Reliability and failure handling

## For Contributors

When working on this repository:
1. **Primary reference**: Use `.github/copilot-instructions.md` for all project guidelines
2. **Workflow patterns**: Reference `instructions/ActivityChatAgentPrompt.instructions.md` for workflow examples
3. **Custom agent**: Invoke `SuperAgent` when you need strict verification enforcement
