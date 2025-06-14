# Development Workspace

**KISS Principle**: Simple structure for development work and GENIE coordination.

## 📁 **Structure**

```
dev/
├── README.md                    # This file
├── workspace/                   # GENIE's perpetual workspace (tracked in git)
│   ├── context/                 # Context files for workflows
│   ├── handoffs/                # Inter-workflow coordination  
│   └── reports/                 # Workflow completion reports
├── scripts/                     # Development scripts (ignored)
└── {project-folders}/           # Active development projects (ignored)
```

## 🎯 **Usage**

### GENIE's Workspace (`/dev/workspace/`)
- **Owner**: GENIE's personal filesystem - full control and organization
- **Purpose**: GENIE's perpetual coordination and file management space
- **Tracked**: Yes, committed to git for persistence
- **Usage**: Context files, handoffs, reports, organized file structures
- **Commits**: GENIE commits workspace changes regularly with proper organization
- **Co-Author**: All commits co-authored by "Automagik Genie <automagik@namastex.ai>"
- **Maintenance**: GENIE regularly sweeps and organizes workspace for efficiency
- **Permissions**: GENIE can create folders/files as needed for system organization

### Development Projects (`/dev/{project-name}/`)
- **Purpose**: Active development work
- **Tracked**: No, gitignored for flexibility
- **Usage**: Project context, progress, temporary work

### Development Scripts (`/dev/scripts/`)
- **Purpose**: Development utilities and experiments
- **Tracked**: No, gitignored

## 🔄 **Simple Rules**

1. **GENIE owns**: `/dev/workspace/` - personal filesystem with full organization control
2. **GENIE maintains**: Regular workspace sweeps, file organization, and commits
3. **GENIE creates**: Folders and files as needed for efficient system organization
4. **Projects use**: `/dev/{project-name}/` for active work (temporary)
5. **Scripts use**: `/dev/scripts/` for development utilities (temporary)
6. **GENIE commits**: Workspace changes committed regularly with co-author pattern

---

**Simple**: GENIE gets a persistent workspace, everything else is flexible and gitignored.