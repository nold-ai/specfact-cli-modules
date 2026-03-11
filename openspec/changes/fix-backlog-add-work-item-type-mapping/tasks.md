## 1. Analysis and Setup

- [x] 1.1 Read existing `backlog_core/commands/add.py` to understand current type resolution
- [x] 1.2 Read `AdoFieldMapper` class to understand `work_item_type_mappings` loading
- [x] 1.3 Read `AdoAdapter.create_issue()` to understand current hardcoded mapping

## 2. Core Implementation

- [x] 2.1 Modify `backlog_core/commands/add.py` to load `AdoFieldMapper` with custom mapping file
- [x] 2.2 Pass mapped work item type through payload to adapter
- [x] 2.3 Update `AdoAdapter.create_issue()` to honor explicit mapped work item types from the payload
- [x] 2.4 Ensure fallback to hardcoded defaults when no custom mapping exists

## 3. Testing

- [x] 3.1 Run existing backlog add tests to ensure no regressions
- [x] 3.2 Test with Scrum project (Product Backlog Item mapping)
- [x] 3.3 Test with Agile project (User Story fallback)
- [x] 3.4 Verify behavior matches `backlog refine` command

## 4. Evidence

- [x] 4.1 Record failing and passing TDD evidence for the change
