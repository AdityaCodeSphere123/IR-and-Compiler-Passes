#include "llvm/IR/Constants.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/PassManager.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"

using namespace llvm;

namespace {

/// Replace integer mul by a positive power of two with a left shift.
///   x * 2^k  -->  x << k     (k >= 1)
class StrengthReducePass : public PassInfoMixin<StrengthReducePass> {
public:
  PreservedAnalyses run(Function &F, FunctionAnalysisManager &) {
    SmallVector<Instruction *, 8> Dead;
    bool Changed = false;

    for (BasicBlock &BB : F) {
      for (Instruction &I : BB) {
        auto *BinOp = dyn_cast<BinaryOperator>(&I);
        if (!BinOp || BinOp->getOpcode() != Instruction::Mul)
          continue;
        if (!BinOp->getType()->isIntegerTy())
          continue;

        Value *LHS = BinOp->getOperand(0);
        Value *RHS = BinOp->getOperand(1);

        Value *Var = nullptr;
        const APInt *Pow = nullptr;
        if (auto *C = dyn_cast<ConstantInt>(RHS)) {
          Var = LHS;
          Pow = &C->getValue();
        } else if (auto *C = dyn_cast<ConstantInt>(LHS)) {
          Var = RHS;
          Pow = &C->getValue();
        } else {
          continue;
        }

        if (Pow->isNegative() || !Pow->isPowerOf2())
          continue;

        unsigned K = Pow->logBase2();
        if (K == 0)
          continue; // x * 1

        IRBuilder<> Builder(BinOp);
        Value *Shl = Builder.CreateShl(Var, K, BinOp->getName() + ".shl",
                                       BinOp->hasNoUnsignedWrap(),
                                       BinOp->hasNoSignedWrap());
        BinOp->replaceAllUsesWith(Shl);
        Dead.push_back(BinOp);
        Changed = true;
      }
    }

    for (Instruction *I : Dead)
      I->eraseFromParent();

    return Changed ? PreservedAnalyses::none() : PreservedAnalyses::all();
  }

  static bool isRequired() { return true; }
};

} // namespace

extern "C" LLVM_ATTRIBUTE_WEAK ::llvm::PassPluginLibraryInfo
llvmGetPassPluginInfo() {
  return {LLVM_PLUGIN_API_VERSION, "StrengthReduce", LLVM_VERSION_STRING,
          [](PassBuilder &PB) {
            PB.registerPipelineParsingCallback(
                [](StringRef Name, FunctionPassManager &FPM,
                   ArrayRef<PassBuilder::PipelineElement>) {
                  if (Name == "strength-reduce") {
                    FPM.addPass(StrengthReducePass());
                    return true;
                  }
                  return false;
                });
          }};
}
