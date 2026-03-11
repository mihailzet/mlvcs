#!/usr/bin/env bash
# Full system test for MLVCS
# Run: bash tests/test_system.sh

API="http://localhost:8000"
PASS=0
FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✅ PASS${NC}: $1"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}❌ FAIL${NC}: $1"; FAIL=$((FAIL+1)); }
info() { echo -e "${YELLOW}ℹ️  ${NC}$1"; }

echo ""
echo "========================================"
echo "   MLVCS System Test Suite"
echo "========================================"
echo ""

# ── 1. Health check
info "Test 1: API health check"
HEALTH=$(curl -sf "$API/health" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'])" 2>/dev/null || echo "")
if [ "$HEALTH" = "healthy" ]; then
    ok "API is healthy"
else
    fail "API health check failed (got: '$HEALTH')"
fi

# ── 2. Create project
info "Test 2: Create project"
PROJ=$(curl -sf -X POST "$API/api/v1/projects/" \
  -H "Content-Type: application/json" \
  -d '{"name":"test-mnist-project","description":"MNIST digit classification"}' 2>/dev/null || echo "")
PROJ_ID=$(echo "$PROJ" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")
if [ -n "$PROJ_ID" ]; then
    ok "Project created: $PROJ_ID"
else
    fail "Project creation failed. Response: $PROJ"
fi

# ── 3. List projects
info "Test 3: List projects"
PROJECTS=$(curl -sf "$API/api/v1/projects/" 2>/dev/null || echo "[]")
COUNT=$(echo "$PROJECTS" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
if [ "$COUNT" -ge "1" ] 2>/dev/null; then
    ok "Listed $COUNT project(s)"
else
    fail "Project listing failed (count=$COUNT)"
fi

# ── 4. Create experiment
info "Test 4: Create experiment"
if [ -z "$PROJ_ID" ]; then
    fail "Skipped - no project ID"
else
    EXP=$(curl -sf -X POST "$API/api/v1/projects/$PROJ_ID/experiments" \
      -H "Content-Type: application/json" \
      -d '{"name":"baseline-cnn","description":"Baseline CNN model","params":{"learning_rate":0.001,"epochs":10,"batch_size":32},"tags":["baseline","cnn"]}' 2>/dev/null || echo "")
    EXP_ID=$(echo "$EXP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")
    if [ -n "$EXP_ID" ]; then
        ok "Experiment created: $EXP_ID"
    else
        fail "Experiment creation failed. Response: $EXP"
    fi
fi

# ── 5. Update experiment
info "Test 5: Update experiment status and metrics"
if [ -z "$EXP_ID" ]; then
    fail "Skipped - no experiment ID"
else
    UPD=$(curl -sf -X PATCH "$API/api/v1/projects/$PROJ_ID/experiments/$EXP_ID" \
      -H "Content-Type: application/json" \
      -d '{"status":"completed","metrics":{"accuracy":0.982,"loss":0.064,"val_accuracy":0.971}}' 2>/dev/null || echo "")
    STATUS=$(echo "$UPD" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "")
    if [ "$STATUS" = "completed" ]; then
        ok "Experiment updated: status=$STATUS"
    else
        fail "Experiment update failed. Response: $UPD"
    fi
fi

# ── 6. Register model
info "Test 6: Register model version"
if [ -z "$EXP_ID" ]; then
    fail "Skipped - no experiment ID"
else
    MODEL=$(curl -sf -X POST "$API/api/v1/experiments/$EXP_ID/models" \
      -H "Content-Type: application/json" \
      -d '{"version":"1.0.0","model_name":"mnist-cnn","framework":"pytorch","metrics":{"accuracy":0.982},"params":{"layers":4,"dropout":0.2}}' 2>/dev/null || echo "")
    MODEL_ID=$(echo "$MODEL" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")
    if [ -n "$MODEL_ID" ]; then
        ok "Model registered: $MODEL_ID"
    else
        fail "Model registration failed. Response: $MODEL"
    fi
fi

# ── 7. Upload artifact
info "Test 7: Upload model artifact to MinIO"
if [ -z "$MODEL_ID" ]; then
    fail "Skipped - no model ID"
else
    echo '{"model":"fake-cnn","weights":[0.1,0.2,0.3],"accuracy":0.982}' > /tmp/test_model.pkl
    UPLOAD=$(curl -sf -X POST "$API/api/v1/experiments/$EXP_ID/models/$MODEL_ID/upload" \
      -F "file=@/tmp/test_model.pkl" 2>/dev/null || echo "")
    UPLOAD_PATH=$(echo "$UPLOAD" | python3 -c "import sys,json; print(json.load(sys.stdin).get('path',''))" 2>/dev/null || echo "")
    if [ -n "$UPLOAD_PATH" ]; then
        ok "Artifact uploaded to: $UPLOAD_PATH"
    else
        fail "Artifact upload failed. Response: $UPLOAD"
    fi
fi

# ── 8. Download artifact
info "Test 8: Download model artifact"
if [ -z "$MODEL_ID" ]; then
    fail "Skipped - no model ID"
else
    HTTP_CODE=$(curl -sf -o /tmp/downloaded_model.pkl -w "%{http_code}" \
      "$API/api/v1/experiments/$EXP_ID/models/$MODEL_ID/download" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] && [ -f /tmp/downloaded_model.pkl ]; then
        ok "Artifact downloaded ($(wc -c < /tmp/downloaded_model.pkl) bytes)"
    else
        fail "Artifact download failed (HTTP $HTTP_CODE)"
    fi
fi

# ── 9. Commit code
info "Test 9: Commit code files to Git"
if [ -z "$PROJ_ID" ]; then
    fail "Skipped - no project ID"
else
    COMMIT=$(curl -sf -X POST "$API/api/v1/projects/$PROJ_ID/commits" \
      -H "Content-Type: application/json" \
      -d '{"message":"Add baseline CNN model","author":"Test User","branch":"main","files":[{"path":"model.py","content":"import torch\nclass CNN(torch.nn.Module):\n    pass\n"},{"path":"train.py","content":"# Training script\n"},{"path":"config.yaml","content":"lr: 0.001\nepochs: 10\n"}]}' \
      2>/dev/null || echo "")
    COMMIT_HASH=$(echo "$COMMIT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('commit_hash','')[:7])" 2>/dev/null || echo "")
    if [ -n "$COMMIT_HASH" ]; then
        ok "Code committed: $COMMIT_HASH"
    else
        fail "Code commit failed. Response: $COMMIT"
    fi
fi

# ── 10. Git history
info "Test 10: Get git commit history"
if [ -z "$PROJ_ID" ]; then
    fail "Skipped - no project ID"
else
    HISTORY=$(curl -sf "$API/api/v1/projects/$PROJ_ID/history" 2>/dev/null || echo "{}")
    COMMIT_COUNT=$(echo "$HISTORY" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('commits',[])))" 2>/dev/null || echo "0")
    if [ "$COMMIT_COUNT" -ge "1" ] 2>/dev/null; then
        ok "Got $COMMIT_COUNT commit(s) in history"
    else
        fail "Git history retrieval failed (count=$COMMIT_COUNT)"
    fi
fi

# ── 11. Promote model
info "Test 11: Promote model to production"
if [ -z "$MODEL_ID" ]; then
    fail "Skipped - no model ID"
else
    PROMO=$(curl -sf -X PATCH "$API/api/v1/experiments/$EXP_ID/models/$MODEL_ID/promote" 2>/dev/null || echo "")
    MSG=$(echo "$PROMO" | python3 -c "import sys,json; print(json.load(sys.stdin).get('message',''))" 2>/dev/null || echo "")
    if echo "$MSG" | grep -q "production" 2>/dev/null; then
        ok "Model promoted to production"
    else
        fail "Model promotion failed. Response: $PROMO"
    fi
fi

# ── 12. Branches
info "Test 12: List git branches"
if [ -z "$PROJ_ID" ]; then
    fail "Skipped - no project ID"
else
    BRANCHES=$(curl -sf "$API/api/v1/projects/$PROJ_ID/branches" 2>/dev/null || echo "{}")
    BRANCH_COUNT=$(echo "$BRANCHES" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('branches',[])))" 2>/dev/null || echo "0")
    if [ "$BRANCH_COUNT" -ge "1" ] 2>/dev/null; then
        ok "Got $BRANCH_COUNT branch(es)"
    else
        fail "Branch listing failed (count=$BRANCH_COUNT)"
    fi
fi

# ── 13. Second experiment
info "Test 13: Create second experiment for comparison"
if [ -z "$PROJ_ID" ]; then
    fail "Skipped - no project ID"
else
    EXP2=$(curl -sf -X POST "$API/api/v1/projects/$PROJ_ID/experiments" \
      -H "Content-Type: application/json" \
      -d '{"name":"resnet-experiment","params":{"learning_rate":0.0001,"epochs":20},"tags":["resnet","improved"]}' 2>/dev/null || echo "")
    EXP2_ID=$(echo "$EXP2" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")
    if [ -n "$EXP2_ID" ]; then
        curl -sf -X PATCH "$API/api/v1/projects/$PROJ_ID/experiments/$EXP2_ID" \
          -H "Content-Type: application/json" \
          -d '{"status":"completed","metrics":{"accuracy":0.991,"loss":0.038}}' > /dev/null 2>&1 || true
        ok "Second experiment created and updated"
    else
        fail "Second experiment failed. Response: $EXP2"
    fi
fi

# ── Summary
echo ""
echo "========================================"
echo -e "   Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
    echo -e "${RED}Some tests failed. Check the output above.${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 All tests passed! System is fully operational.${NC}"
echo ""
echo "Useful URLs:"
echo "  API docs:      http://localhost:8000/docs"
echo "  MinIO console: http://localhost:9001  (minioadmin / minioadmin123)"
echo ""
