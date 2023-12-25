var Module = Module || { };
Module.print = function() { 
   console.log("Hello world");
   Module.simulatorSteps = Module.simulatorSteps || [];
   Module.simulatorSteps.push({ action: "stdout", value: Array.from(arguments).join("") + "\\n\n"});
}
Module.printErr = function() { 
   Module.simulatorSteps = Module.simulatorSteps || [];
   Module.simulatorSteps.push({ action: "stderr", value: Array.from(arguments).join("") + "\\n\n"});
}
Module.notify = function(id, dataPointers) {
    Module.simulatorSteps = Module.simulatorSteps || [];

    var i = 0;
    var steps = [];
    var notifications = Module.simulatorNotifications.filter(n => n.notifyId == id); 
    for (var notification of notifications) {
        if (["assign", "eval", "decl", "par"].includes(notification.action)) {
            var dataTypeName = notification.dataType;
            var dataType = Module.simulatorTypes.find(t => t.name == dataTypeName);
            var dataValue = Module.captureValue(dataPointers[i], dataType);
            
            var snapshot = dataTypeName.endsWith("*") ? Module.captureSnapshot(dataValue, dataTypeName) : undefined;

            steps.push({ ...notification, dataValue, snapshot });
            i++;
        }
        else if (notification.action === "type") {
            var dataType = Module.simulatorTypes.find(t => t.name == "size_t");
            var dataValue = Module.captureValue(dataPointers[i], dataType);

            Module.simulatorTypes.push({ type: "int", name: notification.identifier, byteSize: dataValue });
        }
        else steps.push({ ...notification }); 
    }

    if (Module.simulatorSteps.length > 10000)
        throw new Error("Too many steps (possible infinite loop)");

    for (var step of steps) {
        Module.simulatorSteps.push(step);
        console.log(step);
    }
}

Module.captureValue = function(dataPointer, dataType) {
    var heap;
    switch(dataType.type) {
        case "int": 
            heap = "HEAP" + (dataType.byteSize * 8); 
            break;
        case "uint":
            heap = "HEAPU" + (dataType.byteSize * 8);
            break;
        case "float":
            heap = "HEAPF" + (dataType.byteSize * 8);
            break;
        default:
            throw new Error("Unsupported data type " + dataType.type + " for " + dataType.name);
    }

    if (!Module[heap])
        throw new Error("Unrecognized heap " + heap + " for " + dataType.name);

    return Module[heap][dataPointer / dataType.byteSize];
}

Module.captureSnapshot = function captureHeapSnapshot(pointer, pointerType) {
    const byteSize = Module.getByteSize(pointerType);
    const heapView = Module.getHeap(pointerType);
    const elementSize = byteSize / Uint8Array.BYTES_PER_ELEMENT;

    // Calculate the start and end addresses, ensuring they are within valid bounds
    const startAddress = Math.max(pointer - 100, 0);
    const totalSize = heapView.length * elementSize;
    const endAddress = Math.min(pointer + byteSize + 100, totalSize);

    // Convert the addresses to indices in the typed array
    const startIndex = Math.floor(startAddress / elementSize);
    const endIndex = Math.ceil(endAddress / elementSize);

    // Use slice to get a snapshot of the heap around the pointer
    const data = heapView.slice(startIndex, endIndex);

    return { startAddress, endAddress, data };
}

Module.getByteSize = function(dataType) {
    if (dataType.endsWith("*"))
        return 4;

    switch (dataType) {
        case 'char':
            return 1;
        case 'short':
            return 2;
        case 'int':
        case 'long':
        case 'long int':
        case 'float':
            return 4;
        case 'double':
        case 'long double':
            return 8;
        default:
            throw new Error("Unsupported datatype " + dataType);
    }
}

Module.getHeap = function(dataType) {
    if (dataType.endsWith("*"))
        return Module.HEAP32;

    switch (dataType) {
        case 'char':
            return Module.HEAP8;
        case 'short':
            return Module.HEAP16;
        case 'int':
        case 'long':
        case 'long int':
            return Module.HEAP32;
        case 'float':
            return Module.HEAPF32;
        case 'double':
        case 'long double':
            return Module.HEAPF64;
        default:
            return null;
    }
}

Module.preRun = Module.preRun || [];
Module.preRun.push(function() {
  Module.simulatorCode = {code};
  Module.simulatorNodes = {statements};
  Module.simulatorNotifications = {notifications};
  Module.simulatorTypes = {types};
});