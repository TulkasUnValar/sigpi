#!/bin/bash
# Verification script for search module implementation

echo "=== Verifying Search Module Implementation ==="
echo ""

# Change to frontend directory
cd frontend || exit 1

echo "1. Checking TypeScript compilation..."
npx tsc --noEmit
if [ $? -ne 0 ]; then
    echo "❌ TypeScript compilation failed"
    exit 1
fi
echo "✅ TypeScript compilation passed"
echo ""

echo "2. Running search module tests..."
npm test -- __tests__/features/search/ --passWithNoTests
if [ $? -ne 0 ]; then
    echo "❌ Tests failed"
    exit 1
fi
echo "✅ All tests passed"
echo ""

echo "3. Verifying file structure..."
required_files=(
    "features/search/types.ts"
    "features/search/constants.ts"
    "features/search/queries.ts"
    "features/search/index.ts"
    "features/search/SearchBar.tsx"
    "features/search/SearchResults.tsx"
    "features/search/SearchFilters.tsx"
    "app/search/page.tsx"
    "lib/query-keys.ts"
    "components/shell/Sidebar.tsx"
    "__tests__/features/search/queries.test.ts"
    "__tests__/features/search/SearchBar.test.tsx"
    "__tests__/features/search/SearchResults.test.tsx"
    "__tests__/features/search/page.test.tsx"
)

missing_files=()
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -ne 0 ]; then
    echo "❌ Missing required files:"
    for file in "${missing_files[@]}"; do
        echo "   - $file"
    done
    exit 1
fi
echo "✅ All required files present"
echo ""

echo "=== ✅ All verifications passed! ==="
echo ""
echo "Implementation summary:"
echo "  - Created search feature module with types, constants, queries, and components"
echo "  - Added search query factory to query-keys.ts"
echo "  - Added search navigation item to Sidebar.tsx"
echo "  - Created search page at app/search/page.tsx"
echo "  - Created comprehensive test suite"
echo ""
echo "Ready to commit with: feat(search): implement full-text search UI with filters"
