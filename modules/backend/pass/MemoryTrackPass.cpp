#include "MemoryTrackPass.h"
using namespace llvm;
std::string infoFile = "witnessInfo";
std::string echoCommand = "echo";
// TODO: Work with other types
// FIX: It it not current function

/**
  void MemoryTrackPass::addWitnessInfo(std::string info) {
// int result = system(info.c_str());
// If result != 0 means that something gone wrong
}**/

// TODO: make dynCast only one time
void MemoryTrackPass::instrumentPointer() {
    StoreInst* storeInst = dyn_cast<StoreInst>(&*this->currentInstruction);
    Value* var_address = storeInst->getPointerOperand();
    Value* receives    = storeInst->getValueOperand();

    auto j = this->currentInstruction;

    Twine bitcast("bitcast");

    Value* varPointerCast = CastInst::CreatePointerCast
        (var_address,
         Type::getInt8PtrTy(*this->Ctx),
         bitcast,(Instruction*) j);

    Value* receivesPointerCast = CastInst::CreatePointerCast
        (receives,
         Type::getInt8PtrTy(*this->Ctx),
         bitcast,(Instruction*) j);

    ++j;

    IRBuilder<> builder((Instruction*)j);
    Value* name_llvm = builder.CreateGlobalStringPtr
        (var_address->getName());

    Value* function_llvm = builder.CreateGlobalStringPtr
        (currentFunction->getName());

    Value* args[] = {varPointerCast, receivesPointerCast,
        this->scope_value,
        name_llvm,
        this->line_value,
        function_llvm
    };

    builder.CreateCall(this->map2check_pointer, args);
}

void MemoryTrackPass::instrumentPosixMemAllign() {
    CallInst* callInst = dyn_cast<CallInst>(&*this->currentInstruction);

    this->caleeFunction = callInst->getCalledFunction();

    auto j = this->currentInstruction;
    ++j;

    //Adds map2check_malloc with allocated address and size
    IRBuilder<> builder((Instruction*)j);
    auto size = callInst->getArgOperand(2);
    auto pointer = callInst->getOperand(0);

    Twine bitcast("bitcast");

    Value* varPointerCast = CastInst::CreatePointerCast
        (pointer,
         Type::getInt8PtrTy(*this->Ctx),
         bitcast,(Instruction*) j);

    Value* args[] = {varPointerCast, size};
    builder.CreateCall(map2check_posix, args);
}

// TODO: make dynCast only one time
void MemoryTrackPass::instrumentMalloc() {
    CallInst* callInst = dyn_cast<CallInst>(&*this->currentInstruction);
    auto j = this->currentInstruction;
    ++j;

    //Adds map2check_malloc with allocated address and size
    IRBuilder<> builder((Instruction*)j);
    Value* size = callInst->getArgOperand(0);
    Twine bitcast("bitcast");
    if(size == NULL){

    }
    Value* args[] = {callInst, size};
    builder.CreateCall(map2check_malloc, args);
}

void MemoryTrackPass::instrumentRealloc() {
    CallInst* callInst = dyn_cast<CallInst>(&*this->currentInstruction);
    auto j = this->currentInstruction;
    IRBuilder<> freeBuilder((Instruction*)j);
    auto function_name = this->currentFunction->getName();
    Value* function_llvm = freeBuilder
        .CreateGlobalStringPtr(function_name);

    Value* nullValid = ConstantInt
        ::getSigned(Type::getInt1Ty(*this->Ctx), 1);


    Value* freeArgs[] = {
        callInst->getArgOperand(0),
        this->line_value,
        function_llvm,
        nullValid
    };

    freeBuilder.CreateCall(map2check_free_resolved_address, freeArgs);


    ++j;

    //Adds map2check_malloc with allocated address and size
    IRBuilder<> builder((Instruction*)j);
    auto size = callInst->getArgOperand(1);
    Value* args[] = {callInst, size};
    builder.CreateCall(map2check_malloc, args);
}

void MemoryTrackPass::instrumentMemset() {
    CallInst* callInst = dyn_cast<CallInst>(&*this->currentInstruction);
    auto j = this->currentInstruction;

    auto function_name = this->currentFunction->getName();


    auto size = callInst->getArgOperand(2);
    auto pointer = callInst->getOperand(0);

    Twine bitcast("bitcast");

    Value* varPointerCast = CastInst::CreatePointerCast
        (pointer,
         Type::getInt8PtrTy(*this->Ctx),
         bitcast,(Instruction*) j);

    IRBuilder<> builder((Instruction*)j);
    Value* function_llvm = builder
        .CreateGlobalStringPtr(function_name);
    Value* args[] = {varPointerCast, size};
    builder.CreateCall(map2check_load, args);
    Value* args2[] = {this->line_value, function_llvm};
    builder.CreateCall(map2check_check_deref, args2);
}

void MemoryTrackPass::instrumentMemcpy() {
    CallInst* callInst = dyn_cast<CallInst>(&*this->currentInstruction);
    auto j = this->currentInstruction;

    auto function_name = this->currentFunction->getName();


    auto size = callInst->getArgOperand(2);
    auto pointer_destiny = callInst->getOperand(0);
    auto pointer_origin = callInst->getOperand(1);

    Twine bitcast("bitcast_memcpy");

    Value* varPointerCast = CastInst::CreatePointerCast
        (pointer_destiny,
         Type::getInt8PtrTy(*this->Ctx),
         bitcast,(Instruction*) j);

    Value* sizeCast = CastInst::CreateIntegerCast(size, Type::getInt32Ty(*this->Ctx), false, bitcast, (Instruction*) j);


    Value* varPointerCastOrigin = CastInst::CreatePointerCast
        (pointer_origin,
         Type::getInt8PtrTy(*this->Ctx),
         bitcast,(Instruction*) j);

    IRBuilder<> builder((Instruction*)j);
    Value* function_llvm = builder
        .CreateGlobalStringPtr(function_name);

    Value* args2[] = {varPointerCastOrigin, sizeCast};
    builder.CreateCall(map2check_load, args2);

    Value* args3[] = {this->line_value, function_llvm};
    builder.CreateCall(map2check_check_deref, args3);

    Value* args[] = {varPointerCast, sizeCast};
    builder.CreateCall(map2check_load, args);

    builder.CreateCall(map2check_check_deref, args3);


}

void MemoryTrackPass::instrumentAlloca() {
    CallInst* callInst = dyn_cast<CallInst>(&*this->currentInstruction);
    auto j = this->currentInstruction;
    ++j;

    //Adds map2check_malloc with allocated address and size
    IRBuilder<> builder((Instruction*)j);
    auto size = callInst->getArgOperand(0);

    Twine non_det("bitcast_map2check_alloca");
    Value* pointerCast = CastInst
        ::CreatePointerCast(callInst,
                Type::getInt8PtrTy(*this->Ctx),
                non_det,
                (Instruction*) j);

    auto function_name = "";
    Value* function_llvm = builder.CreateGlobalStringPtr(function_name);

    Value* args[] = {function_llvm, pointerCast, size,size,this->line_value, this->scope_value};

    builder.CreateCall(map2check_alloca, args);
}


/* For the porpose of memory checking calloc is basically
 * a malloc with 2 args, the first is how many elements
 * and the second is the size of the primitive element
 */
void MemoryTrackPass::instrumentCalloc() {
    CallInst* callInst = dyn_cast<CallInst>(&*this->currentInstruction);
    auto j = this->currentInstruction;
    ++j;

    IRBuilder<> builder((Instruction*)j);
    auto quantityOfElements = callInst->getArgOperand(0);
    auto sizeOfElements = callInst->getArgOperand(1);
    Value* args[] = {callInst, quantityOfElements,sizeOfElements};
    builder.CreateCall(map2check_calloc, args);
}

// TODO: make dynCast only one time
void MemoryTrackPass::instrumentFree() {
    CallInst* callInst = dyn_cast<CallInst>(&*this->currentInstruction);
    auto j = this->currentInstruction;
    // ++j;

    this->caleeFunction = callInst->getCalledFunction();
    this->getDebugInfo();
    LoadInst* li;
    IRBuilder<> builder((Instruction*)j);

    auto function_name = this->currentFunction->getName();
    Value* function_llvm = builder
        .CreateGlobalStringPtr(function_name);

    if (this->caleeFunction == NULL) {
        Value* v = callInst->getCalledValue();
        this->caleeFunction = dyn_cast<Function>(v->stripPointerCasts());
        li = dyn_cast<LoadInst>(callInst->getArgOperand(0));


    }
    else {
        // Value* addr = callInst->getArgOperand(0)->stripPointerCasts();

        li = dyn_cast<LoadInst>(callInst->
                getArgOperand(0)->
                stripPointerCasts());


    }
    if(li == NULL) {

        Value* nullNotValid = ConstantInt
            ::getSigned(Type::getInt1Ty(*this->Ctx), 0);


        Value* args[] = {
            callInst->getArgOperand(0),
            this->line_value,
            function_llvm,
            nullNotValid
        };

        builder.CreateCall(map2check_free_resolved_address, args);
    }
    else {

        auto name = li->getPointerOperand()->getName();
        Value* name_llvm = builder
            .CreateGlobalStringPtr(name);

        Twine non_det("bitcast_map2check");
        Value* pointerCast = CastInst
            ::CreatePointerCast(li->getPointerOperand(),
                    Type::getInt8PtrTy(*this->Ctx),
                    non_det,
                    (Instruction*) j);

        Value* args[] = { name_llvm,
            pointerCast,
            this->scope_value,
            this->line_value,
            function_llvm,

        };

        builder.CreateCall(map2check_free, args);
    }

}

void MemoryTrackPass::getDebugInfo() {
    unsigned scope_number;
    unsigned line_number;
    DebugLoc location = this->currentInstruction->getDebugLoc();
    if(location) {
        scope_number = location.getScope()->getMetadataID();
        line_number = location.getLine();

    }
    else {
        scope_number = 0;
        line_number  = 0;
    }


    this->scope_value = ConstantInt
        ::getSigned(Type::getInt32Ty(*this->Ctx), scope_number);
    this->line_value = ConstantInt
        ::getSigned(Type::getInt32Ty(*this->Ctx), line_number);
}

int MemoryTrackPass::getLineNumber() {
    unsigned line_number;
    DebugLoc location = this->currentInstruction->getDebugLoc();
    if(location) {
        line_number = location.getLine();
    }
    else {
        line_number  = 0;
    }
    return line_number;
}


void MemoryTrackPass::instrumentInit() {

    Function::iterator bb = this->currentFunction->begin();  
    BasicBlock::iterator i = bb->begin();

    IRBuilder<> builder((Instruction*)i);
    Module* currentModule = this->currentFunction->getParent();

    std::vector<GlobalVariable*> globals;
    for(auto globalVar = currentModule->global_begin();
            globalVar != currentModule->global_end();
            globalVar++) {

        GlobalVariable* variable = dyn_cast<GlobalVariable>(&*globalVar);
        globals.push_back(variable);
    }


    for (unsigned pos = 0; pos < globals.size(); pos++) {
        GlobalVariable* variable = globals[pos];
        //errs () << "VAR: " << variable->getName() << "\n";
        const DataLayout dataLayout = currentModule->getDataLayout();
        auto type = variable->getType()->getPointerElementType();
        unsigned typeSize = dataLayout.getTypeSizeInBits(type)/8;
        unsigned primitiveSize = 0;

        if(type->isArrayTy()) {
            type = type->getArrayElementType();
        }

        if(type->isVectorTy()) {
            type = type->getVectorElementType();
        }

        primitiveSize = dataLayout.getTypeSizeInBits(type)/8;

        Value* name_llvm = builder.CreateGlobalStringPtr(variable->getName());

        ConstantInt* typeSizeValue = ConstantInt::getSigned(Type::getInt32Ty(*this->Ctx), typeSize);
        ConstantInt* primitiveSizeValue = ConstantInt::getSigned(Type::getInt32Ty(*this->Ctx), primitiveSize);


        Twine non_det("bitcast_map2check");
        Value* pointerCast = CastInst::CreatePointerCast(variable,Type::getInt8PtrTy(*this->Ctx),non_det,(Instruction*) i);

        //TODO: 
        this->currentInstruction = i;
        this->getDebugInfo();
        /**
          errs() << *name_llvm << " (1) \n"; 
          errs() << *pointerCast << " (2) \n"; 
          errs() << *typeSizeValue << " (3) \n"; 
          errs() << *primitiveSizeValue << " (4) \n"; 
          errs() << *this->line_value << " (5) \n";
          errs() << *this->scope_value << " (6) \n";
          errs() << "----------------- \n";
         **/

        //const char* name, void* ptr, int size, int size_of_primitive, int line, int scope)
        Value* args[] = {name_llvm, pointerCast, typeSizeValue, primitiveSizeValue, this->line_value, this->scope_value};
        builder.CreateCall(map2check_alloca, args);
    }

}

// TODO: use hash table instead of nested "if's"
void MemoryTrackPass::switchCallInstruction() {
    // TODO: Resolve SVCOMP ISSUE  
    if (this->caleeFunction->getName() == "free") {
        this->instrumentFree();
    }
    else if (this->caleeFunction->getName() == "cfree") {
        this->instrumentFree();
    }
    else if (this->caleeFunction->getName() == "posix_memalign") {
        this->instrumentPosixMemAllign();
    }
    else if (this->caleeFunction->getName() == "realloc") {
        this->instrumentRealloc();
    }
    else if (this->caleeFunction->getName() == "memset") {
        this->instrumentMemset();
    }
    else if (this->caleeFunction->getName() == "memcpy") {
        this->instrumentMemcpy();
    }
    else if (this->caleeFunction->getName() == "malloc") {
        this->instrumentMalloc();
    }
    else if (this->caleeFunction->getName() == "valloc") {
        this->instrumentMalloc();
    }
    else if (this->caleeFunction->getName() == "alloca") {
        this->instrumentAlloca();
    }
    else if (this->caleeFunction->getName() == "calloc") {
        this->instrumentCalloc();
    }

}


void MemoryTrackPass::instrumentFunctionAddress() {
    if(!this->mainFunctionInitialized) {
        this->functionsValues.push_back(this->currentFunction);
        return;
    }

    Function::iterator bb = this->mainFunction->begin();
    // // bb--;

    BasicBlock::iterator i = bb->begin();
    i++;


    IRBuilder<> builder((Instruction*) i);
    for (unsigned iterator = 0;
         iterator < this->functionsValues.size(); iterator++) {
        Value* name_llvm = builder.CreateGlobalStringPtr
            (this->functionsValues[iterator]->getName());

        Twine non_det("bitcast_map2check");
        Value* pointerCast = CastInst
            ::CreatePointerCast(this->functionsValues[iterator],
                    Type::getInt8PtrTy(*this->Ctx),
                    non_det,
                    (Instruction*) i);

        Value* instrumentationArgs[] = {name_llvm, pointerCast};
        builder.CreateCall(map2check_function, instrumentationArgs);

    }

    this->functionsValues.clear();
}

void MemoryTrackPass::instrumentAllocation() {
    AllocaInst* allocaInst = dyn_cast<AllocaInst>(&*this->currentInstruction);


    auto j = this->currentInstruction;
    j++;

    Module* M = this->currentFunction->getParent();
    const DataLayout dataLayout = M->getDataLayout();


    auto type = allocaInst->getType()->getPointerElementType();

    unsigned typeSize = dataLayout.getTypeSizeInBits(type)/8;

    unsigned primitiveSize = 0;

    if(type->isArrayTy()) {

        type = type->getArrayElementType();
    }



    if(type->isVectorTy()) {
        type = type->getVectorElementType();
    }

    primitiveSize = dataLayout.getTypeSizeInBits(type)/8;
    IRBuilder<> builder((Instruction*)j);
    Value* name_llvm = builder.CreateGlobalStringPtr
        (allocaInst->getName());

    ConstantInt* typeSizeValue = ConstantInt::getSigned(Type::getInt32Ty(*this->Ctx), typeSize);
    ConstantInt* primitiveSizeValue = ConstantInt::getSigned(Type::getInt32Ty(*this->Ctx), primitiveSize);


    Twine non_det("bitcast_map2check");
    Value* pointerCast = CastInst
        ::CreatePointerCast(allocaInst,
                Type::getInt8PtrTy(*this->Ctx),
                non_det,
                (Instruction*) j);

    Value* args[] = {name_llvm, pointerCast, typeSizeValue, primitiveSizeValue, this->line_value, this->scope_value};
    builder.CreateCall(map2check_alloca, args);
}

// TODO: make dynCast only one time
void MemoryTrackPass::runOnCallInstruction() {
    CallInst* callInst = dyn_cast<CallInst>(&*this->currentInstruction);  

    this->caleeFunction = callInst->getCalledFunction();

    if (this->caleeFunction == NULL) {
        Value* v = callInst->getCalledValue();
        this->caleeFunction = dyn_cast<Function>(v->stripPointerCasts());

        if(this->caleeFunction != NULL) {
            this->switchCallInstruction();
        }
    }
    else {
        this->switchCallInstruction();    
    }

    this->caleeFunction = NULL;
}

// TODO: make dynCast only one time
void MemoryTrackPass::runOnStoreInstruction() {
    StoreInst* storeInst = dyn_cast<StoreInst>(&*this->currentInstruction);
    if(storeInst->getValueOperand()->getType()->isPointerTy()) {
        this->instrumentPointer();


    }

    Value* var_address = storeInst->getPointerOperand();
    Value* receives    = storeInst->getValueOperand();


    Module* M = this->currentFunction->getParent();
    const DataLayout dataLayout = M->getDataLayout();

    auto type = receives->getType();
    unsigned typeSize = dataLayout.getTypeSizeInBits(type)/8;
    ConstantInt* typeSizeValue = ConstantInt::getSigned(Type::getInt32Ty(*this->Ctx), typeSize);

    auto j = this->currentInstruction;
    //    j--;

    Twine non_det("bitcast_map2check_store");
    Value* pointerCast = CastInst
        ::CreatePointerCast(var_address,
                Type::getInt8PtrTy(*this->Ctx),
                non_det,
                (Instruction*) j);
    //    j++;
    IRBuilder<> builder((Instruction*)j);
    Value* args[] = {pointerCast, typeSizeValue};
    builder.CreateCall(map2check_load, args);

    Value* function_name_llvm = builder.CreateGlobalStringPtr
        (this->currentFunction->getName());
    Value* args2[] = {this->line_value, function_name_llvm};
    builder.CreateCall(map2check_check_deref, args2);

}

void MemoryTrackPass::instrumentNotStaticArrayAlloca() {
    AllocaInst* allocaInst = dyn_cast<AllocaInst>(&*this->currentInstruction);
    Value* v = allocaInst->getArraySize();
    //    Value* v = allocaInst->getOperand(0);

    auto j = this->currentInstruction;
    j++;

    Module* M = this->currentFunction->getParent();
    const DataLayout dataLayout = M->getDataLayout();

    auto type = allocaInst->getType()->getPointerElementType();
    unsigned primitiveSize = 0;
    //    type->get

    primitiveSize = dataLayout.getTypeSizeInBits(type)/8;
    IRBuilder<> builder((Instruction*)j);
    Value* name_llvm = builder.CreateGlobalStringPtr
        (allocaInst->getName());


    ConstantInt* primitiveSizeValue = ConstantInt::getSigned(Type::getInt32Ty(*this->Ctx), primitiveSize);

    Twine non_det("bitcast_map2check");
    Value* pointerCast = CastInst
        ::CreatePointerCast(allocaInst,
                Type::getInt8PtrTy(*this->Ctx),
                non_det,
                (Instruction*) j);

    Value* sizeCast = CastInst
        ::CreateIntegerCast(v,
                Type::getInt32Ty(*this->Ctx),
                true,
                non_det,
                (Instruction*) j);

    Value* args[] = {name_llvm, pointerCast, sizeCast, primitiveSizeValue,this->line_value, this->scope_value};
    builder.CreateCall(map2check_non_static_alloca, args);
}

void  MemoryTrackPass::instrumentArrayAlloca() {

    AllocaInst* allocaInst = dyn_cast<AllocaInst>(&*this->currentInstruction);
    Value* v = allocaInst->getArraySize();
    //    Value* v = allocaInst->getOperand(0);

    auto j = this->currentInstruction;
    j++;

    Module* M = this->currentFunction->getParent();
    const DataLayout dataLayout = M->getDataLayout();

    auto type = v->getType();
    unsigned primitiveSize = 0;


    primitiveSize = dataLayout.getTypeSizeInBits(type)/8;
    IRBuilder<> builder((Instruction*)j);
    Value* name_llvm = builder.CreateGlobalStringPtr
        (allocaInst->getName());


    ConstantInt* primitiveSizeValue = ConstantInt::getSigned(Type::getInt32Ty(*this->Ctx), primitiveSize);

    Twine non_det("bitcast_map2check");
    Value* pointerCast = CastInst
        ::CreatePointerCast(allocaInst,
                Type::getInt8PtrTy(*this->Ctx),
                non_det,
                (Instruction*) j);

    Value* sizeCast = CastInst
        ::CreateIntegerCast(v,
                Type::getInt32Ty(*this->Ctx),
                true,
                non_det,
                (Instruction*) j);


    Value* args[] = {name_llvm, pointerCast, sizeCast, primitiveSizeValue, this->line_value, this->scope_value};
    builder.CreateCall(map2check_alloca, args);
}

void MemoryTrackPass::runOnAllocaInstruction() {
    AllocaInst* allocaInst = dyn_cast<AllocaInst>(&*this->currentInstruction);

    if(allocaInst->isArrayAllocation()) {
        if(allocaInst->isStaticAlloca()) {

            this->instrumentArrayAlloca();
        } else {
            this->instrumentNotStaticArrayAlloca();
        }

    }
    else {
        this->instrumentAllocation();
    }


}


void MemoryTrackPass::runOnLoadInstruction() {
    LoadInst* loadInst = dyn_cast<LoadInst>(&*this->currentInstruction);

    Value* v = loadInst->getPointerOperand()->stripPointerCasts();

    Module* M = this->currentFunction->getParent();
    const DataLayout dataLayout = M->getDataLayout();

    auto type = loadInst->getPointerOperand()->getType()->getPointerElementType();
    unsigned typeSize = dataLayout.getTypeSizeInBits(type)/8;
    ConstantInt* typeSizeValue = ConstantInt::getSigned(Type::getInt32Ty(*this->Ctx), typeSize);

    auto j = this->currentInstruction;
    //    j--;

    Twine non_det("bitcast_map2check");
    Value* pointerCast = CastInst
        ::CreatePointerCast(v,
                Type::getInt8PtrTy(*this->Ctx),
                non_det,
                (Instruction*) j);
    //    j++;
    IRBuilder<> builder((Instruction*)j);
    Value* args[] = {pointerCast, typeSizeValue};
    builder.CreateCall(map2check_load, args);

    Value* function_name_llvm = builder.CreateGlobalStringPtr
        (this->currentFunction->getName());
    Value* args2[] = {this->line_value, function_name_llvm};
    builder.CreateCall(map2check_check_deref, args2);

}

void MemoryTrackPass::prepareMap2CheckInstructions() {
    Function& F = *this->currentFunction;

    this->map2check_load = F.getParent()->
        getOrInsertFunction("map2check_load",
                Type::getVoidTy(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                Type::getInt32Ty(*this->Ctx),
                NULL);


    this->map2check_free_resolved_address = F.getParent()->
        getOrInsertFunction("map2check_free_resolved_address",
                Type::getVoidTy(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                Type::getInt32Ty(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                Type::getInt1Ty(*this->Ctx),
                NULL);

    this->map2check_pointer = F.getParent()->
        getOrInsertFunction("map2check_add_store_pointer",
                Type::getVoidTy(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                Type::getInt32Ty(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                Type::getInt32Ty(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                NULL);

    this->map2check_check_deref = F.getParent()->
        getOrInsertFunction("map2check_check_deref",
                Type::getVoidTy(*this->Ctx),
                Type::getInt32Ty(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                NULL);

    this->map2check_malloc = F.getParent()->
        getOrInsertFunction("map2check_malloc",
                Type::getVoidTy(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                Type::getInt64Ty(*this->Ctx),
                NULL);

    this->map2check_posix = F.getParent()->
        getOrInsertFunction("map2check_posix",
                Type::getVoidTy(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                Type::getInt64Ty(*this->Ctx),
                NULL);

    this->map2check_calloc = F.getParent()->
        getOrInsertFunction("map2check_calloc",
                Type::getVoidTy(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                Type::getInt64Ty(*this->Ctx),
                Type::getInt64Ty(*this->Ctx),
                NULL);

    this->map2check_alloca = F.getParent()->
        getOrInsertFunction("map2check_alloca",
                Type::getVoidTy(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                Type::getInt32Ty(*this->Ctx),
                Type::getInt32Ty(*this->Ctx),
                Type::getInt32Ty(*this->Ctx),
                Type::getInt32Ty(*this->Ctx),
                NULL);

    this->map2check_non_static_alloca = F.getParent()->
        getOrInsertFunction("map2check_non_static_alloca",
                Type::getVoidTy(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                Type::getInt32Ty(*this->Ctx),
                Type::getInt32Ty(*this->Ctx),
                Type::getInt32Ty(*this->Ctx),
                Type::getInt32Ty(*this->Ctx),
                NULL);

    this->map2check_function = F.getParent()->
        getOrInsertFunction("map2check_function",
                Type::getVoidTy(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                NULL);

    this->map2check_free = F.getParent()->
        getOrInsertFunction("map2check_free",
                Type::getVoidTy(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                Type::getInt32Ty(*this->Ctx),
                Type::getInt32Ty(*this->Ctx),
                Type::getInt8PtrTy(*this->Ctx),
                NULL);

}


void MemoryTrackPass::instrumentFunctionArgumentAddress() {
    Function* F = this->currentFunction;
    Module* M = this->currentFunction->getParent();
    const DataLayout dataLayout = M->getDataLayout();

    Function::iterator bb = this->currentFunction->begin();
    // // bb--;

    BasicBlock::iterator i = bb->begin();
    i++;
    //    i++;


    for(auto arg = F->arg_begin(); arg != F->arg_end(); arg++) {
        Argument* functionArg = &(*arg);

        //        functionArg->
        auto type = functionArg->getType();
        unsigned typeSize = dataLayout.getTypeSizeInBits(type)/8;
        IRBuilder<> builder((Instruction*)i);
        Value* name_llvm = builder.CreateGlobalStringPtr
            (functionArg->getName());

        ConstantInt* typeSizeValue = ConstantInt::getSigned(Type::getInt32Ty(*this->Ctx), typeSize);
        Value* argCast;


        if(type->isPointerTy()) {

            Twine mapcheck_bitcast_argument("mapcheck_bitcast_argument");
            argCast = CastInst::CreatePointerCast(functionArg,
                    Type::getInt8PtrTy(*this->Ctx),
                    mapcheck_bitcast_argument,
                    (Instruction*) i);

        } else {

            argCast = functionArg;
        }





        //        ConstantInt* primitiveSizeValue = ConstantInt::getSigned(Type::getInt32Ty(*this->Ctx), primitiveSize);


        Value* args[] = {name_llvm, argCast, typeSizeValue, typeSizeValue,this->line_value, this->scope_value};
        builder.CreateCall(map2check_alloca, args);
    }

}

bool MemoryTrackPass::runOnFunction(Function &F) {
    this->Ctx = &F.getContext();
    this->currentFunction = &F;
    this->prepareMap2CheckInstructions();
    //this->instrumentInit(); //overhead BUG

    if(F.getName() == "main") {
        //auto globalVars = currentModule->getGlobalList();
        this->functionsValues.push_back(this->currentFunction);
        this->mainFunctionInitialized = true;
        this->mainFunction = &F;
        this->instrumentInit(); // Related to BUG checkout this                
    }

    //this->instrumentFunctionAddress();  

    for (Function::iterator bb = F.begin(), e = F.end(); bb != e; ++bb) {
        for (BasicBlock::iterator i = bb->begin(), e = bb->end(); i != e; ++i) {
            this->currentInstruction = i;

            //i->dump();

            if (dyn_cast<CallInst>(&*i) != NULL) {
                //callInst->dump();
                this->getDebugInfo();              
                this->runOnCallInstruction();                 
                //errs() << "runOnCallInstruction() \n";
            } else if (dyn_cast<StoreInst>(&*this->currentInstruction) != NULL) {
                this->getDebugInfo();	      
                this->runOnStoreInstruction();
                //errs() << "runOnStoreInstruction() \n";
            } else if (dyn_cast<AllocaInst>(&*this->currentInstruction) != NULL) {
                this->getDebugInfo();	      
                this->runOnAllocaInstruction();
                //errs() << "runOnAllocaInstruction() \n";
            } else if (dyn_cast<LoadInst>(&*this->currentInstruction) != NULL) {
                this->getDebugInfo();	      
                this->runOnLoadInstruction();
                //errs() << "runOnLoadInstruction() \n";
            }


        }
    }

    return true;
}

char MemoryTrackPass::ID = 0;
static RegisterPass<MemoryTrackPass> X("memory_track", "Validate memory security proprieties using dynamic memory tracking");
