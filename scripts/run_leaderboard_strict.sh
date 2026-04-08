#!/usr/bin/env bash
set -euo pipefail

source .venv312/bin/activate
mkdir -p artifacts

# Ordered free-capable substitution pool.
SUB_POOL=(
  "Qwen/Qwen2.5-72B-Instruct"
  "Qwen/Qwen2.5-7B-Instruct"
  "HuggingFaceH4/zephyr-7b-beta"
  "mistralai/Mistral-Nemo-Instruct-2407"
)

# Requested logical rows to try.
REQUESTED=(
  "Qwen/Qwen2.5-72B-Instruct"
  "meta-llama/Llama-3.3-70B-Instruct"
  "mistralai/Mistral-7B-Instruct-v0.3"
)

OUT_SUMMARY="artifacts/leaderboard_summary.csv"
echo "requested_model,selected_model,status,reason,upi,sgi,cib,child,avg,fallbacks,log_file" > "${OUT_SUMMARY}"

sanitize() {
  echo "$1" | tr '/:' '__'
}

extract_score() {
  local log_file="$1"
  local task="$2"
  awk -v task="$task" '
    $1=="[BASELINE]" {
      t=""; s="";
      for(i=1;i<=NF;i++){
        if($i ~ /^task=/){t=substr($i,6)}
        if($i ~ /^score=/){s=substr($i,7)}
      }
      if(t==task){print s}
    }
  ' "$log_file" | tail -1
}

extract_avg() {
  local log_file="$1"
  awk '/^Final average score:/ {print $4}' "$log_file" | tail -1
}

extract_fallbacks() {
  local log_file="$1"
  awk '
    /^\[ROUTER_SUMMARY\]/{
      for(i=1;i<=NF;i++){
        if($i ~ /^fallbacks=/){
          print substr($i,11)
        }
      }
    }
  ' "$log_file" | tail -1
}

run_model() {
  local model="$1"
  local log_file="$2"
  set +e
  REQUIRE_HF_ROUTER=true VERBOSE=true MODEL_NAME="$model" python inference.py > "$log_file" 2>&1
  local code=$?
  set -e
  local fallbacks
  fallbacks="$(extract_fallbacks "$log_file")"
  [[ -z "${fallbacks}" ]] && fallbacks="unknown"
  if [[ "$code" -eq 0 && "$fallbacks" == "0" ]] && grep -q "fallbacks=0" "$log_file"; then
    return 0
  fi
  return 1
}

for requested in "${REQUESTED[@]}"; do
  reason=""
  success=0
  selected=""
  log_file=""

  declare -a candidates=("$requested")
  for m in "${SUB_POOL[@]}"; do
    skip=0
    for e in "${candidates[@]}"; do
      [[ "$e" == "$m" ]] && skip=1
    done
    [[ "$skip" -eq 0 ]] && candidates+=("$m")
  done

  for candidate in "${candidates[@]}"; do
    file_suffix="$(sanitize "$candidate")"
    log_file="artifacts/router_${file_suffix}.txt"
    if run_model "$candidate" "$log_file"; then
      selected="$candidate"
      success=1
      if [[ "$candidate" != "$requested" ]]; then
        reason="substituted"
      else
        reason="requested_ok"
      fi
      break
    fi
  done

  if [[ "$success" -eq 1 ]]; then
    upi="$(extract_score "$log_file" "upi-scam-triage")"
    sgi="$(extract_score "$log_file" "sgi-compliance-review")"
    cib="$(extract_score "$log_file" "cib-graph-takedown")"
    child="$(extract_score "$log_file" "child-safety-escalation")"
    avg="$(extract_avg "$log_file")"
    fallbacks="$(extract_fallbacks "$log_file")"
    echo "${requested},${selected},ok,${reason},${upi},${sgi},${cib},${child},${avg},${fallbacks},${log_file}" >> "${OUT_SUMMARY}"
  else
    last_idx=$((${#candidates[@]} - 1))
    last_candidate="${candidates[$last_idx]}"
    last_file="artifacts/router_$(sanitize "${last_candidate}").txt"
    echo "${requested},n/a,failed,no_strict_success,n/a,n/a,n/a,n/a,n/a,n/a,${last_file}" >> "${OUT_SUMMARY}"
  fi
done

echo "Wrote ${OUT_SUMMARY}"
