#!/bin/sh
# Fetch the public GIFT-Eval and fev-bench results at the exact commits used in the article.
# gift_eval.py reads gift_eval_repo/results/, fev.py reads fev_repo/benchmarks/fev_bench/.
set -e
cd "$(dirname "$0")/.."

GIFT_COMMIT=3c7be6deffb0046e1c08f9103db8bc84b3cf7ebd   # SalesforceAIResearch/gift-eval, 2026-10-17
FEV_COMMIT=f9e2c7d3152ed7d15c3b1c2877bb3ae7d977046f    # autogluon/fev, 2026-10-16

if [ ! -d gift_eval_repo ]; then
  git clone --quiet --filter=blob:none --no-checkout https://github.com/SalesforceAIResearch/gift-eval.git gift_eval_repo
  git -C gift_eval_repo sparse-checkout set results
  git -C gift_eval_repo checkout --quiet "$GIFT_COMMIT"
fi
if [ ! -d fev_repo ]; then
  git clone --quiet --filter=blob:none --no-checkout https://github.com/autogluon/fev.git fev_repo
  git -C fev_repo sparse-checkout set benchmarks/fev_bench
  git -C fev_repo checkout --quiet "$FEV_COMMIT"
fi
echo "gift_eval_repo at $(git -C gift_eval_repo rev-parse --short HEAD), fev_repo at $(git -C fev_repo rev-parse --short HEAD)"
