#!/bin/bash
# Emergency fix for du-holder holds blocking replication

echo "🔍 Finding all du-holder snapshots with holds..."

# Find all du-holder snapshots
DU_HOLDER_SNAPSHOTS=$(zfs list -t snapshot -H -o name | grep "du-holder" || true)

if [[ -z "$DU_HOLDER_SNAPSHOTS" ]]; then
    echo "✅ No du-holder snapshots found!"
    exit 0
fi

COUNT=$(echo "$DU_HOLDER_SNAPSHOTS" | wc -l)
echo "Found $COUNT du-holder snapshots"
echo ""

# Check each for holds
HOLDS_FOUND=0
for snap in $DU_HOLDER_SNAPSHOTS; do
    holds=$(sudo zfs holds -H "$snap" 2>/dev/null | grep -v "^NAME" || true)
    if [[ -n "$holds" ]]; then
        echo "🔒 Found hold on: $snap"
        echo "$holds" | while read -r name tag timestamp; do
            echo "   Tag: $tag"
        done
        ((HOLDS_FOUND++))
    fi
done

if [[ $HOLDS_FOUND -eq 0 ]]; then
    echo "✅ No holds found on any du-holder snapshots!"
    
    # Ask if user wants to destroy the snapshots
    echo ""
    echo "These snapshots can be safely destroyed. Would you like to remove them?"
    read -p "Destroy all $COUNT du-holder snapshots? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        for snap in $DU_HOLDER_SNAPSHOTS; do
            if sudo zfs destroy "$snap" 2>/dev/null; then
                echo "✅ Destroyed: $snap"
            else
                echo "❌ Failed to destroy: $snap"
            fi
        done
    fi
    exit 0
fi

echo ""
echo "⚠️  Found $HOLDS_FOUND snapshots with holds that may block replication!"
echo ""
read -p "Release all du_analysis_hold holds? [y/N] " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Release all holds
RELEASED=0
FAILED=0

for snap in $DU_HOLDER_SNAPSHOTS; do
    if sudo zfs holds -H "$snap" 2>/dev/null | grep -q "du_analysis_hold"; then
        if sudo zfs release du_analysis_hold "$snap" 2>&1; then
            echo "✅ Released hold on: $snap"
            ((RELEASED++))
        else
            echo "❌ Failed to release hold on: $snap"
            ((FAILED++))
        fi
    fi
done

echo ""
echo "📊 Summary: Released $RELEASED holds, $FAILED failed"

# Now offer to destroy snapshots
echo ""
echo "Would you like to destroy these snapshots now that holds are released?"
read -p "Destroy all du-holder snapshots? [y/N] " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    DESTROYED=0
    FAILED_DESTROY=0
    
    for snap in $DU_HOLDER_SNAPSHOTS; do
        if sudo zfs destroy "$snap" 2>/dev/null; then
            echo "✅ Destroyed: $snap"
            ((DESTROYED++))
        else
            echo "❌ Failed to destroy: $snap"
            ((FAILED_DESTROY++))
        fi
    done
    
    echo ""
    echo "📊 Destroyed $DESTROYED snapshots, $FAILED_DESTROY failed"
fi

echo ""
echo "✅ Cleanup complete!"
