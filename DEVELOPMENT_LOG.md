# Development Log

## Project: Angel One Data Pipeline

This document tracks the development progress of the Angel One Data Pipeline project, which extracts data from Angel One API and stores it in DuckDB.

## Project Timeline

### Phase 1: Setup and Basic API Connection

- [x] Initialize project structure
- [x] Setup AngelOneConnector class for API communication
- [x] Implement authentication and connection testing
- [x] Create virtual environment and install dependencies
- [x] Add proper error handling for connection issues
- [x] Create configuration management system

### Phase 2: Data Extraction

- [x] Implement token values (master stock records) extraction
- [x] Create data validation schemas
- [x] Optimize token storage with unified schema
- [x] Fetch and organize market data
- [x] Add data transformation utilities

### Phase 3: DuckDB Integration

- [x] Setup DuckDB connection and schema
- [x] Create data storage routines
- [x] Implement unified token storage
- [x] Implement incremental data updates
- [x] Add data versioning capabilities

### Phase 4: Pipeline Automation (Current)

- [x] Build automated data refresh process
- [x] Add scheduling capabilities
- [x] Implement logging and monitoring
- [x] Implement real-time market data processing
- [x] Add cross-platform compatibility for Windows
- [x] Implement options analytics with strike normalization
- [x] Create alert system for failures
- [x] Implement FastAPI module for data access
- [x] Create real-time Parquet exports for API consumption
- [x] Centralize database management in DBManager

## Current Sprint Tasks

1. ✅ Fix refreshToken parameter issue in getProfile() method
2. ✅ Implement real-time market data processing
3. ✅ Fix Windows console logging compatibility issues
4. ✅ Enhance SQL statements for better error handling
5. ✅ Implement options analytics with strike distance calculation
6. ✅ Implement ATM options filtering for real-time data
7. ✅ Add FastAPI module for market data access
8. ✅ Resolve DuckDB concurrency issues for the API module
9. ✅ Centralize database schema management in DBManager
10. ✅ Implement per-iteration Parquet exports for API consumption
11. [ ] Add data visualization for real-time market data

## Implementation Notes

### 2025-03-12: Database Management Centralization

- Implemented comprehensive database management centralization:
  - Moved all table creation to DBManager._init_tables() method
  - Created a central method for initializing the market_summary_view
  - Added a built-in export_market_summary_to_parquet method to DBManager
  - Eliminated redundant table creation in other manager classes
  - Consolidated all database-related code in a single class
- Key benefits:
  - Single point of schema management
  - Consistent table schema across all components
  - Elimination of redundant table creation
  - Prevention of schema inconsistencies
  - Proper separation of concerns
- Technical improvements:
  - Reduced code duplication
  - Improved maintainability
  - Better error handling for database operations
  - More consistent logging of database operations
  - Simplified database upgrade path
- Future enhancements:
  - Database versioning system
  - Schema migration support
  - Database status monitoring

### 2025-03-12: Per-Iteration Parquet Exports

- Implemented real-time exports of market summary data:
  - Added Parquet file export after each real-time data collection iteration
  - Created a standalone export utility for manual exports
  - Added support for direct SQL execution from file for exports
  - Enhanced error handling for export operations
- Key features:
  - Always-fresh data for API consumption
  - No need to wait for pipeline completion
  - Standalone utility for manual exports
  - Automatic recreation of market_summary_view if missing
  - Clean separation of database and API data access
- Technical implementation:
  - Added export code in run_realtime_monitoring function
  - Created utils/export_market_summary.py utility script
  - Integrated with centralized DBManager
  - Added proper error handling and logging
- Benefits:
  - Real-time data availability for API
  - Elimination of database concurrency issues
  - Improved API performance through direct file access
  - Reduced database load
  - More reliable API operation

### 2025-03-12: API Frontend Integration Documentation

- Created comprehensive API integration documentation:
  - Added JavaScript fetch and axios examples for API calls
  - Documented all API endpoints and parameters
  - Provided sample response format
  - Added detailed usage examples
  - Updated README.md with API integration details
- Key features:
  - Complete code examples for frontend integration
  - Detailed endpoint documentation
  - Error handling in example code
  - Multiple implementation options
- Benefits:
  - Easy integration with any frontend framework
  - Consistency in API usage
  - Robust error handling
  - Cross-origin support
  - Self-documenting API with Swagger UI

### 2025-03-15: ATM Options Filtering Implementation

- Implemented intelligent ATM options filtering:
  - Created two-pass approach to first fetch futures data, then only fetch relevant ATM options
  - Added `get_atm_options_tokens` method to filter options based on current futures prices
  - Enhanced `RealtimeMarketDataManager` to support efficient ATM-only processing
  - Added configurable strike buffer to control the range of strikes included
- Key benefits:
  - Reduced API requests by 90-95% for options data collection
  - Minimized database storage requirements with focused data collection
  - Improved performance with more relevant data selection
  - Enhanced usability with configurable ATM strike range
- Technical implementation:
  - Added strike distance awareness using database values and sensible defaults
  - Created command-line parameter support for controlling ATM filtering behavior
  - Enhanced documentation with clear examples of feature usage
  - Implemented comprehensive error handling for futures price extraction
- Use cases enabled:
  - Efficient real-time monitoring of ATM options for trading decisions
  - Reduced storage footprint for continuous data collection
  - More focused analysis with only the most relevant options data
  - Customizable near-ATM range to match specific trading strategies

### 2025-03-10: Cross-Platform Compatibility and Error Fixes

- Implemented fixes for real-time market data functionality:
  - Fixed ConfigManager.get() default parameter handling for better fault tolerance
  - Added refreshToken parameter to getProfile() method to fix API client requirements
  - Enhanced SQL statements to use explicit conflict targets for better error handling
  - Implemented ASCII-compatible logging for Windows console compatibility
- Key improvements:
  - Reliable console output on Windows systems without Unicode errors
  - More robust error handling in database operations
  - Complete compatibility with Angel One API requirements
  - Improved configuration system resilience
- Technical implementation:
  - Added custom logging formatter for ASCII-compatible output
  - Updated SQL statements to use proper ON CONFLICT clauses
  - Enhanced configuration access with fallback default values
  - Improved exception handling throughout the codebase
- Troubleshooting support:
  - Added documentation for common issues and solutions
  - Provided guidance for extending the codebase with compatibility in mind
  - Enhanced error messages for easier debugging

### 2025-03-10: Options Analytics Implementation

- Implemented comprehensive options analytics enhancements:
  - Added strike price normalization to divide API values by 100
  - Developed strike distance calculation algorithm for each stock
  - Enhanced database schema to store strike distance information
  - Updated token processing pipeline to incorporate options analytics
- Key features:
  - Automatic detection of standard strike distances using frequency analysis
  - Normalized strike prices that match market representation
  - Comprehensive strike grid mapping for strategy development
  - Complete database integration with strike distance storage
- Technical implementation:
  - Enhanced `process_options_tokens` method with strike price adjustment
  - Added calculation of differences between adjacent strikes for each stock
  - Implemented mode-based statistical analysis to determine standard distance
  - Added `strike_distance` column to database schema with migration support
  - Enhanced logging with strike distance visualization
- Challenges addressed:
  - Handled database schema migration for existing databases
  - Implemented column existence checking using information_schema
  - Fixed token storage to properly include the strike_distance column
  - Added debug logging to verify strike distance calculations
- Use cases enabled:
  - More accurate options strategy development
  - Strike price grid mapping for volatility analysis
  - Improved options chain visualization
  - Strike selection for advanced option strategies

### 2025-03-13: Real-time Market Data Implementation

- Created comprehensive real-time market data processing system:
  - Implemented `RealtimeMarketDataManager` class for fetching real-time market data
  - Added support for Angel One's getMarketData API with FULL mode
  - Created database schema for storing detailed market data including order book depth
  - Implemented batched processing with API rate limiting (50 tokens per request)
- Key features:
  - Real-time data for equity, futures, and options instruments
  - Efficient batching to respect API limits (1 request per second)
  - Complete market data including LTP, OHLC, volumes, and order book depth
  - Continuous monitoring with configurable refresh intervals
- Technical implementation:
  - Added `get_market_data` method to AngelOneConnector
  - Created database schema for real-time market data
  - Implemented token batching to respect API limits
  - Added continuous monitoring script with market hours awareness
- Use cases addressed:
  - Real-time market monitoring for trading decisions
  - Order book depth analysis for liquidity assessment
  - Price movement tracking across instrument types
  - Continuous data collection during market hours

### 2025-03-08: Successful Token Processing Pipeline

- Successfully implemented and tested complete token processing pipeline:
  - Correctly mapping futures to equity tokens using name-based matching
  - Successfully storing 216 equity tokens with corresponding futures references
  - Implemented proper error handling and logging throughout the pipeline
  - Verified data integrity with sample data verification
- Key achievements:
  - Resolved symbol mapping issues by using name-based matching
  - Enhanced logging for better debugging and verification
  - Successfully tested end-to-end token processing workflow
  - Achieved reliable storage of both futures and equity tokens

### 2025-03-08: Token Processing and Database Integration

- Enhanced TokenManager with F&O specific functionality:
  - Added filtering for futures stocks (FUTSTK in NFO)
  - Implemented current expiry detection
  - Added corresponding equity spot token mapping
- Created DBManager for DuckDB integration:
  - Implemented database schema for futures and equity tokens
  - Added data storage and validation routines
  - Included sample data verification
- Updated main.py with comprehensive testing:
  - Added token processing pipeline tests
  - Implemented database operation tests
  - Enhanced error handling and logging

### 2025-03-08: Token Manager Implementation

- Created TokenManager class for handling token master data
- Implemented token data fetching from Angel One API
- Added token data structure analysis functionality
- Updated main.py with token manager testing
- Features added:
  - Automatic token data fetching
  - Error handling for API requests
  - Sample data structure logging
  - Integration with existing test suite

### 2025-03-08: Project Setup and Dependencies

- Created Python virtual environment (venv)
- Successfully installed all required packages:
  - smartapi-python v1.5.5 for Angel One API integration
  - duckdb v0.9.2 for data storage
  - Additional utility packages (pyotp, logzero, pandas)
- Verified all dependencies installed correctly
- Project ready for development
- Set up Git repository:
  - Created .gitignore file with Python-specific patterns
  - Initialized Git repository
  - Made initial commit with project setup
  - Created GitHub repository at <https://github.com/bhavesh0009/NFO_dashboard_backend.git>
  - Successfully pushed code to GitHub
- Created main.py test script:
  - Added connection testing functionality
  - Implemented profile retrieval test
  - Added detailed logging for debugging
  - Used logzero for structured logging output

### 2025-03-08: Project Initialization

- Created initial project structure
- Implemented basic Angel One API connection
- Successfully tested authentication

### YYYY-MM-DD: Token Extraction

- [To be completed]

### Token Values (Master Stock Records)

- **Status**: ✅ Completed
- **Description**: Store the master record of all available stocks/tokens from Angel One
- **Requirements**:
  - ✅ Extract complete token dataset
  - ✅ Store with all relevant metadata
  - ✅ Create lookup capabilities
  - ✅ Implement regular updates
- **Notes**: Successfully implemented and tested with proper data validation

### 2025-03-09: Database Schema Optimization

- Implemented unified token storage approach:
  - Consolidated multiple token tables into a single master table
  - Added token type differentiation ('FUTURES' or 'EQUITY')
  - Improved referential integrity between futures and equity tokens
  - Enhanced data validation and type handling
- Key improvements:
  - Streamlined database schema for better performance
  - Added proper column type handling for numeric values
  - Implemented explicit column mapping for reliable data insertion
  - Enhanced error logging and debugging capabilities
- Successfully tested:
  - Processed over 120,000 raw tokens
  - Filtered and stored 216 current expiry futures
  - Mapped and stored 216 corresponding equity tokens
  - Verified data integrity and relationships

### 2025-03-09: Configuration Management Implementation

- Implemented YAML-based configuration system:
  - Created centralized config/config.yaml for all settings
  - Developed ConfigManager class with singleton pattern
  - Added support for nested configuration access
  - Implemented configuration reloading capability
- Key configurations added:
  - API endpoints and parameters
  - Market trading hours
  - Database settings (using nfo_derivatives_hub.duckdb as central data store)
  - Token types and instrument types
  - Exchange segments
  - Date format standardization
- Benefits achieved:
  - Removed hardcoded values from codebase
  - Centralized configuration management
  - Easy modification of settings without code changes
  - Better maintainability and scalability
- Successfully migrated:
  - Token manager configuration
  - Database settings
  - Date format specifications
  - Exchange and instrument type definitions
- Database scope defined:
  - Token master data storage
  - Historical price data (planned)
  - Spot values for dashboard (planned)
  - Market analytics and metrics (planned)

### 2025-03-09: Options Token Processing Implementation

- Added comprehensive options token processing:
  - Implemented `process_options_tokens` method in TokenManager
  - Added configuration for options instrument type (OPTSTK)
  - Enhanced token type system to include OPTIONS
  - Added strike price validation and analysis
- Key features implemented:
  - Current expiry options filtering
  - Strike price distribution analysis
  - Standardized date format handling
  - Integration with existing token storage
- Benefits achieved:
  - Complete F&O token coverage
  - Better market analysis capabilities
  - Enhanced data validation
  - Improved debugging with strike price statistics
- Successfully tested:
  - Options token extraction
  - Strike price validation
  - Integration with futures and equity tokens
  - Combined storage in unified schema

### 2025-03-10: Token Refresh Optimization

- Implemented smart token refresh mechanism:
  - Added check for last token update timestamp
  - Automatic skipping of refresh if tokens are already up-to-date for the current day
  - Added hard refresh parameter for forcing updates when needed
  - Optimized API calls by preventing unnecessary data fetching
- Benefits achieved:
  - Reduced API load and potential rate limiting issues
  - Faster application startup when tokens are already current
  - Better system performance during multiple daily executions
  - More predictable and reliable operation
- Technical implementation:
  - Added timestamp tracking for token updates
  - Integrated with market hours configuration
  - Enhanced logging for refresh decisions
  - Added developer force refresh option

### 2025-03-10: API Call Optimization

- Enhanced token refresh logic for maximum efficiency:
  - Moved refresh check **before** any API calls
  - Completely skips 120K+ token API call when refresh not needed
  - Improved code flow in TokenManager for better API call management
  - Significantly reduced unnecessary network traffic
- Performance improvement:
  - Reduced startup time from 2+ minutes to seconds when tokens already exist
  - Eliminated unnecessary processing of large datasets
  - Decreased API server load from redundant calls
  - Better handling of rate limits on Angel One API
- Technical enhancements:
  - Refactored token processing workflow
  - Consolidated API call decision logic in one place
  - Improved logging for better visibility of optimization
  - Updated main program flow to align with optimized approach

### 2025-03-10: Historical Data Processing Implementation

- Created comprehensive historical data processing system:
  - Implemented `HistoricalDataManager` class for fetching equity historical data
  - Added database schema for historical OHLCV records
  - Created batched processing with API rate limiting
  - Implemented data validation and storage routines
- Key features:
  - Fetches historical data back to 2010 for all equity tokens
  - Uses daily interval for comprehensive market analysis
  - Handles API responses with proper error handling
  - Stores data with efficient duplicate handling
- Technical implementation:
  - Added `store_historical_data` method to DBManager
  - Created test utilities for verifying data fetch and storage
  - Implemented comprehensive production-ready script for full data processing
  - Added logging with file output for progress tracking
- Use cases addressed:
  - Complete historical data for equity market analysis
  - Chart generation for technical analysis
  - Backtesting trading strategies
  - Market trend analysis over extended periods

### 2025-03-11: Codebase Consolidation and CLI Enhancement

- Refactored testing and execution structure:
  - Consolidated separate test scripts into a unified main.py interface
  - Added comprehensive command-line interface with subcommands
  - Implemented argument parsing for flexible execution options
  - Maintained full functionality with simplified structure
- Key improvements:
  - Simplified codebase with less file fragmentation
  - Created consistent entry point for all operations
  - Enhanced usability with standardized CLI interface
  - Maintained full functionality of separate scripts
- Technical implementation:
  - Used argparse for creating subcommands and options
  - Implemented modular function design for each operation
  - Added proper exit code handling for scripting support
  - Created sensible defaults for common operations
- Benefits:
  - Reduced codebase complexity
  - Improved developer experience
  - Better consistency across operations
  - Lower barrier to entry for new users

### 2025-03-12: Historical Data Range Extension

- Extended historical data range capability:
  - Changed default from date from 5 days ago to January 1, 2000
  - Maintained the Angel One API date format requirements
  - Enabled comprehensive historical analysis over decades
  - Preserved API load management with rate limiting
- Technical changes:
  - Updated `_get_date_params` method in HistoricalDataManager
  - Fixed rate limiting to 0.25 seconds between requests
  - Reduced batch delay to 2 seconds for improved throughput
  - Enhanced progress reporting for long-running operations
- Benefits:
  - Complete historical backfill capability for equity tokens
  - Deeper market trend analysis across multiple market cycles
  - More robust backtesting capabilities with extended data
  - Improved historical performance metrics

### 2025-03-10: Database Recovery Mechanism

- Implemented automatic database corruption recovery:
  - Added detection of database corruption errors
  - Implemented recovery process to recreate database when corrupted
  - Enhanced error handling to prevent cascading failures
  - Added graceful degradation for database connection issues
- Benefits achieved:
  - Self-healing database functionality
  - Increased application resilience
  - Better handling of improper database manipulations
  - Clear logging for debugging corruption issues
- Technical implementation:
  - Added specialized exception handling for DuckDB serialization errors
  - Implemented database file recreation process
  - Enhanced error checking in DBManager initialization
  - Added robust connection management
- Use cases addressed:
  - Recovery from improper shutdowns
  - Handling of direct SQL manipulation outside the API
  - Protection against database file corruption
  - Automatic recovery without manual intervention

### 2025-03-10: Database Management Utilities

- Added comprehensive database utility tools:
  - Implemented `truncate_tables` method in DBManager class
  - Created standalone utility scripts for database operations
  - Added support for database backup and restore
  - Implemented database status checking
- Key features:
  - Safe table truncation with confirmation safeguards
  - Automated backup naming with timestamps
  - Status reporting with detailed database metrics
  - Integrated error handling and logging
- Use cases addressed:
  - Test data cleanup without database corruption
  - Safe database state management for development
  - Quick database status checks
  - Database backup before destructive operations
- Implementation details:
  - Added utilities directory with standalone scripts
  - Created command-line interfaces with argparse
  - Implemented robust error handling with user-friendly messages
  - Added detailed documentation for all utility functions

### 2025-03-15: FastAPI Module Implementation

- Created comprehensive FastAPI module for market data access:
  - Implemented RESTful API endpoints for market_summary_view
  - Added filtering capabilities for market data
  - Created Pydantic data models for API validation
  - Added complete API documentation
- Key features:
  - Complete market summary data access through REST API
  - Symbol-specific data retrieval
  - Flexible filtering by price and percentage change
  - Comprehensive API documentation with Swagger UI
- Technical implementation:
  - Created dedicated API package with clean separation of concerns
  - Implemented efficient database access patterns
  - Added proper error handling for database operations
  - Utilized pydantic models for request and response validation
- Use cases enabled:
  - Frontend integration with market data
  - Mobile app access to market summary data
  - External system integration through RESTful API
  - Data visualization and dashboard capabilities
- Challenges addressed:
  - Efficient querying of market summary view
  - Proper type handling for database values
  - Implementation of proper API response structures
  - Integration with existing codebase

### 2025-03-12: DuckDB Concurrency Resolution Using Parquet Files

- Implemented elegant solution to DuckDB concurrency issues:
  - Created export function to save market_summary_view to Parquet file after each pipeline run
  - Modified API to read from Parquet file instead of accessing the database directly
  - Eliminated file locking issues by completely decoupling read and write operations
  - Maintained full functionality while improving reliability
- Technical implementation:
  - Added `export_market_summary_to_parquet()` function to the pipeline
  - Created dedicated exports directory for Parquet files
  - Updated API database utilities to use pandas for Parquet file reading
  - Modified API server to check for Parquet file instead of database connection
- Benefits:
  - Completely eliminated database file locking issues
  - Removed risk of database corruption or deletion
  - Improved API performance through direct file access
  - Simplified database access patterns
  - Provided a clean separation between data producers and consumers
- Future enhancements:
  - Potential for auto-refreshing cached data in API server
  - Option for real-time exports during the pipeline run
  - Multiple version retention for historical comparison
  - Compression options for larger datasets

## Challenges & Solutions

### Challenge 1: ConfigManager.get() Default Parameter Issue

**Issue**: The `RealtimeMarketDataManager` was using a `default` parameter with `config.get()`, which wasn't supported by the implementation.  
**Solution**: Updated the code to check for None values after retrieval and provide defaults afterward, maintaining backward compatibility with existing code.

### Challenge 2: Missing refreshToken parameter in getProfile()

**Issue**: The Angel One API's `getProfile()` method required a refreshToken parameter that wasn't being provided.  
**Solution**: Updated the method to pass the stored auth_token as the refreshToken parameter, ensuring compliance with the API requirements.

### Challenge 3: SQL INSERT Conflicts with Multiple Primary Keys

**Issue**: The `INSERT OR REPLACE` SQL statement was failing due to need for explicit conflict targets with composite primary keys.  
**Solution**: Enhanced the SQL to use `INSERT ... ON CONFLICT ... DO UPDATE` with explicit conflict targets for the composite primary key.

### Challenge 4: Unicode Errors in Windows Console

**Issue**: Unicode symbols in log messages were causing encoding errors in the Windows console.  
**Solution**: Implemented a custom logging formatter to replace Unicode characters with ASCII equivalents, ensuring cross-platform compatibility.

### Challenge 5: DuckDB Concurrency Limitations

**Issue**: The API was unable to access the database when the market data pipeline was running due to file locking.  
**Solution**: Implemented a Parquet file export after each data refresh, allowing the API to read from the Parquet file instead of the database.

### Challenge 6: Database Schema Management

**Issue**: Table creation code was scattered across different manager classes, leading to potential inconsistencies.  
**Solution**: Centralized all table creation in the DBManager._init_tables() method to ensure consistent schema management.

## Feature Tracking

### [Future Feature Name]

- **Status**: Planned
- **Description**: [Feature description]
- **Requirements**: [List requirements]
- **Notes**: [Any relevant notes]

## Version History

- **v0.1.0** (Planned) - Initial working version with Angel One connection
- **v0.2.0** (Planned) - Token extraction and storage
- **v1.0.0** (Planned) - Complete pipeline with automation
