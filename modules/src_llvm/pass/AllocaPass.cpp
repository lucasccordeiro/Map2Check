#include <llvm/Pass.h>
#include <llvm/IR/Module.h>
#include <llvm/IR/Function.h>
#include <llvm/IR/Instructions.h>
#include <llvm/IR/IRBuilder.h>
#include <llvm/IR/Metadata.h>
#include <llvm/IR/Constants.h>


#include <llvm/Support/raw_ostream.h>
#include <iostream>

using namespace llvm;


  struct AllocaPass : public FunctionPass {
    static char ID;
    AllocaPass() : FunctionPass(ID) {}

    virtual bool runOnFunction(Function &F) {
      LLVMContext& Ctx = F.getContext();
      Constant* map2check_pointer = F.getParent()
      ->getOrInsertFunction("map2check_pointer",
                  Type::getVoidTy(Ctx),
                  Type::getInt8PtrTy(Ctx),
                  Type::getInt8PtrTy(Ctx),
                  Type::getInt8PtrTy(Ctx),
                  Type::getInt32Ty(Ctx),
                  NULL);


    /*
	 * Iterates over all instructions "i" of all functions and blocks
	 */
     for (Function::iterator bb = F.begin(), e = F.end(); bb != e; ++bb) {
	   for (BasicBlock::iterator i = bb->begin(), e = bb->end(); i != e; ++i) {

		 /*
		  * The next block check if the current instruction is a Allocation, if
		  * so, if the allocation is a pointer, it instruments the "map2check_pointer"
		  * function with its address and size
		  */
		 if (AllocaInst* allocInst = dyn_cast<AllocaInst>(&*i)) {

		   auto name = allocInst->getName();

			/*
			 * Check the name of the variable, if it is empty, it means that it
			 * is a temp var, and we do not need to care of it
			 */
		   if (name.compare("")){
			      auto type = allocInst->getAllocatedType();
			      // Checks if allocated type is a pointer
			      if (type->isPointerTy()) {
			        auto j = i;
			        ++j;

              unsigned line_number;

              DebugLoc location = allocInst->getDebugLoc();
              if(location) {
                line_number = location.getLine();
              }
              else {
                line_number  = 0;
              }

              ConstantInt* line_value = ConstantInt::getSigned(Type::getInt32Ty(Ctx), line_number);


              IRBuilder<> builder_alloc((Instruction*) j);
              Value* name_llvm = builder_alloc.CreateGlobalStringPtr(name);
              Value* scope_llvm = builder_alloc.CreateGlobalStringPtr(F.getName());

              Twine non_det("bitcast");
      	      Value* pointerCast = CastInst::CreatePointerCast(allocInst, Type::getInt8PtrTy(Ctx), non_det,(Instruction*) j);

              // Adds klee call with allocated address
              ++j;
              IRBuilder<> builder((Instruction*) j);
              Value* args[] = {pointerCast,  scope_llvm, name_llvm, line_value };
              // builder.CreateCall(map2check_pointer, args);
            }
		   }
		 }
	   }
	   return true;
	 }
	}
};
	char AllocaPass::ID = 0;
  static RegisterPass<AllocaPass> X("alloca_inst", "Checks for allocations instructions");