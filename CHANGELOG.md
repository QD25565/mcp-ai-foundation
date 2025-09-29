<div align="center">
<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=35&duration=1&pause=10000&color=878787&background=00000000&center=true&vCenter=true&width=500&lines=CHANGELOG" alt="CHANGELOG" />
</div>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=16&duration=1&pause=10000&color=82A473&background=00000000&center=true&vCenter=true&width=700&lines=Notable+changes+to+the+MCP+AI+Foundation+tools" alt="Notable changes to the MCP AI Foundation tools" />

### **[2025-09-29] - Test Suite Fixes**
![](images/header_underline.png)

#### GitHub Actions Fixes
- **Fixed import errors** - Updated test workflow for new module structure
- **notebook_mcp** → `notebook_main`, `notebook_shared`, `notebook_storage`
- **teambook_mcp** → `teambook_main_mcp`, `teambook_api_mcp`, `teambook_storage_mcp`, `teambook_shared_mcp`
- **Added version verification** - Tests now verify all tools are at correct versions
- **Added functionality tests** - Verify core functions exist in each module

#### Test Infrastructure
- **Created test_all.py** - Comprehensive test script for local validation
- **Enhanced CI/CD** - More thorough testing across Python 3.8-3.12
- **Better dependency handling** - Optional dependencies handled gracefully

### **[2025-09-29] - Documentation Corrections**
![](images/header_underline.png)

#### MCP Configuration Fixes
- **Fixed teambook path** - Changed from `teambook_mcp.py` to `teambook_main_mcp.py`
- **Updated all documentation** - Removed references to non-existent primitives
- **Corrected architecture** - Teambook documented as built on notebook foundation

#### Teambook v7.0.0 Documentation
- **Accurate implementation** - Now reflects actual 4-module architecture
- **Built on notebook** - Not separate primitives system
- **Evolution challenges** - Properly documented `evolve`, `attempt`, `combine`
- **Ownership system** - Clear documentation of `claim`, `release`, `assign`
- **Team management** - Documented teambook creation and switching

### **[2025-09-29] - Documentation Update**
![](images/header_underline.png)

#### Documentation Improvements
- **Notebook v6.2.0** - Updated docs to reflect three-file architecture and new features
- **Teambook v7.0.0** - Updated docs for evolution challenges and ownership mechanics
- **Consistent Formatting** - Applied standard header/title format across all docs
- **Tool Icons** - Added icon references for each tool
- **Accurate Versions** - All documentation now reflects actual tool versions

### **[7.0.0] - 2025-09-28**
![](images/header_underline.png)

#### Teambook v7.0.0
- **Evolution Challenges** - `evolve()`, `attempt()`, `attempts()`, `combine()` for iterative improvement
- **Ownership System** - `claim()`, `release()`, `assign()` for task ownership
- **Team Coordination** - `create_teambook()`, `join_teambook()`, `use_teambook()`, `list_teambooks()`
- **Built on Notebook** - Inherits all notebook capabilities
- **Cross-Tool Integration** - Auto-logs to notebook, supports time queries

### **[6.2.0] - 2025-09-27**
![](images/header_underline.png)

#### Notebook v6.2.0
- **Three-File Architecture** - Refactored from single 2500+ line file into:
  - `notebook_main.py` - Core API and MCP handler
  - `notebook_storage.py` - Database and vector operations  
  - `notebook_shared.py` - Utilities and constants
- **Directory Tracking** - Automatically tracks directories mentioned in notes
- **Database Maintenance** - New `compact()` function runs VACUUM to optimize DuckDB
- **Bug Fix** - Fixed `pinned_only` filter in recall function
- **Recent Directories** - New `recent_dirs()` function tracks last 10 accessed paths

### **[6.1.0] - 2025-09-27**
![](images/header_underline.png)

#### Notebook v6.1.0 - Context and Clarity

##### Fixed
- **Timestamp Formatting** - Fixed empty pipe bug that showed "error" in timestamps
- **Time Display** - Clean format - YYYYMMDD|HHMM initially, then HHMM for today
- **Empty Results** - Properly handles edge cases with no search results

##### Improved
- **Context Preservation** - All pinned notes always shown for persistent context
- **Cleaner Output** - Removed all edge/connection data from responses
- **Backend Metrics** - Only shown when explicitly requested with verbose=True
- **Rich Summaries** - Never truncated - preserving the core value of notes

### **[6.0.0] - 2025-09-27**
![](images/header_underline.png)

#### Notebook v6.0.0 - DuckDB Edition

##### Architecture Changes
- **DuckDB Backend** - Migrated from SQLite to DuckDB for columnar analytics
- **Native Array Storage** - Tags stored as arrays, eliminating join tables
- **Vectorized PageRank** - Uses DuckDB's recursive CTEs for graph calculations
- **Automatic Migration** - Safe transition from SQLite with backup

##### Performance Improvements
- PageRank calculation: 66 seconds → <1 second
- Graph traversals: 40x faster
- Complex queries: 25x faster  
- Memory usage: 90% reduction

### **[5.2.1] - 2025-09-26**
![](images/header_underline.png)

#### Notebook v5.2.1
- Safe tag data migration preserving all existing tags
- Automatic database backup before schema changes
- Sparse matrix PageRank using scipy
- Normalized tag system with dedicated tables
- Cached entity extraction patterns

### **[5.0.0] - 2025-09-26**
![](images/header_underline.png)

#### Notebook v5.0.0 - Semantic Intelligence
- **EmbeddingGemma Integration** - Google's 300M parameter model
- **Hybrid Search** - Combines semantic vectors with keyword search
- **ChromaDB Storage** - Persistent vector database
- **Dynamic Paths** - Automatic path resolution
- **Background Migration** - Existing notes automatically vectorized

### **[3.1.0] - 2025-09-25**
![](images/header_underline.png)

#### Task Manager v3.1.0
- **Notebook Integration** - Auto-logs all operations
- **Time-Based Filtering** - Natural language queries like "yesterday"
- **Source Tracking** - Shows which notes created tasks
- **Cross-Tool Creation** - Tasks from notebook TODOs

### **[3.0.0] - 2025-09-24**
![](images/header_underline.png)

#### World v3.0.0
- **Ultra-Minimal Output** - 80% token reduction
- **Single-Line Format** - Pipe-delimited by default
- **Smart Weather** - Only shows extreme conditions
- **Batch Operations** - Process multiple requests

### **[3.0.0] - 2025-09-15**
![](images/header_underline.png)

#### SQLite Migration
- All tools migrated from JSON to SQLite
- Automatic migration from legacy formats
- Full-text search capabilities
- Atomic operations and thread safety

### **[2.0.0] - 2025-09-01**
![](images/header_underline.png)

#### Foundation Release
- Notebook with basic memory and recall
- Task Manager with priority support
- World context provider
- Initial MCP implementation

<div align="center">

Built for AIs, by AIs. 🤖

</div>
