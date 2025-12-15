# Exercise 4: Magentic Basics

This exercise demonstrates Magentic orchestration - an advanced multi-agent coordination pattern that automatically manages task decomposition, agent selection, and result synthesis. Unlike concurrent or sequential patterns, Magentic uses an intelligent orchestrator that:

- Plans how to decompose the task
- Delegates subtasks to appropriate agents
- Monitors progress and adapts the plan
- Synthesizes final results

## Magentic-One Overview

It is based on the [Magentic One concept](https://www.microsoft.com/en-us/research/articles/magentic-one-a-generalist-multi-agent-system-for-solving-complex-tasks/?msockid=0493d15deb436a993cebc291eaef6baa) which was originally implemented with autogen. This exercise uses the agent-framework MagenticBuilder API to achieve similar functionality, as the [Magentic One](https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/orchestrations/magentic?pivots=programming-language-python) concept is also implemented in the framework using the [MagenticBuilder class](https://learn.microsoft.com/en-us/python/api/agent-framework-core/agent_framework.magenticbuilder?view=agent-framework-python-latest).

![magentic](image.png)

Magentic-One is a multi-agent orchestration pattern designed for complex, open-ended tasks that require dynamic collaboration. It was originally introduced by AutoGen and later inspired Microsoft’s Agent Framework orchestration model.
Key Principles:

- Dedicated Manager Agent: A Magentic manager coordinates specialized agents, deciding which agent acts next based on context, task progress, and capabilities.
- Shared Context & Adaptive Workflow: Maintains a global state, tracks progress, and adapts plans in real time.
- Iterative Refinement: Breaks down problems into subtasks, delegates them, and refines solutions through multiple reasoning rounds.
- Dynamic Collaboration: Agents can be invoked multiple times in any order, enabling flexibility.
- Human-in-the-Loop (Optional): Supports manual intervention for critical decisions.

Why It’s Useful:

- Ideal for scenarios where the solution path is not predefined.
- Handles tasks requiring research, computation, and reasoning cycles.
- Enables scalable, modular workflows with specialized agents (e.g., ResearchAgent, CoderAgent).

Example Use Case:

- Generating a comprehensive report comparing energy efficiency of ML models:
  - Research agent gathers data.
  - Coder agent analyzes and computes results.
  - Manager aggregates findings into a structured report.

## Key Concepts

1. MagenticBuilder: High-level API for multi-agent orchestration
2. Standard Manager: Built-in orchestrator with planning capabilities
3. Specialized Agents: Domain experts (Researcher, Coder)
4. Streaming Callbacks: Real-time event monitoring
5. Event Types: Orchestrator messages, agent deltas, agent messages, final results

## Workflow Parameters

- max_round_count: Maximum orchestration rounds (default: 10)
- max_stall_count: Retries when progress stalls (default: 3)
- max_reset_count: Full plan resets allowed (default: 2)

## Prerequisites

- .env file configured with your Github key and LLM details.
- Agent Framework installed: pip install agent-framework
- Special models for some agents:
  - ResearcherAgent: gpt-4o-search-preview (web search capability)
  - CoderAgent: OpenAI Assistants with code interpreter


## Setup

1. Clone the repository.
2. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .agentic
   source .agentic/bin/activate  # On Windows use `.agentic\Scripts\activate`
   pip install -r requirements.txt
   ```

   If you already have the agent-framework installed globally or followed the main README guidance, you can skip this step.

3. Configure your `.env` file with the necessary API keys and model settings.

4. Run the Magentic orchestration script from the repository's root folder:
   
    ```bash
   python samples/magentic/main.py
   ```

5. Observe the console output for real-time orchestration events and the final synthesized result.
