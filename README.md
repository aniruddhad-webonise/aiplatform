# AI Platform

A decoupled AI platform with a central orchestrator and specialized agent services.

## Overview

This platform implements a service-oriented architecture with:
- A central AI orchestrator for request routing and workflow management
- Specialized agent services (Chat, RAG, SQL, Email, etc.)
- Configuration-driven design for maximum flexibility
- Multi-tenant support with tenant-specific configurations
- Factory patterns for dynamic component creation

## Architecture

```
┌─────────────────────────────────────────┐
│              Client Layer               │
│   (API Gateway, Auth, Rate Limiting)    │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│         Orchestrator Service            │
│  (Request Processing, Agent Selection,  │
│   Workflow Management, Tenant Config)   │
└───┬───────────┬────────────┬────────────┘
    │           │            │
┌───▼───┐   ┌───▼───┐    ┌───▼───┐
│Agent 1│   │Agent 2│    │Agent 3│  ...
│Service│   │Service│    │Service│
└───┬───┘   └───┬───┘    └───┬───┘
    │           │            │
    └───────────┼────────────┘
                │
┌───────────────▼───────────────┐
│      MCP Server Factory       │
│(Creates appropriate MCP server│
│      based on config)         │
└───────────────┬───────────────┘
                │
┌───────────────▼───────────────┐
│       External Systems        │
│  (Databases, Vector Stores,   │
│   Email Systems, APIs, etc)   │
└───────────────────────────────┘
```

## Project Structure

- `/core` - Core system components
  - `/orchestrator` - Central orchestration system
  - `/interfaces` - Base interfaces and abstract classes
  - `/factories` - Factory classes for dynamic component creation
  - `/config` - Configuration management
- `/services` - Implementation of services
  - `/agents` - Agent service implementations
- `/api` - API endpoints and client interfaces

## Setup and Installation

TBD

## Usage

TBD 