mergeInto(LibraryManager.library, {
    notify: function(metadataPtr, dataPtr) {
        var step = {}; 

        // Parse raw data
        var metadata = UTF8ToString(metadataPtr);
        var parsedMetadata = metadata
            .split(';')
            .map(s => s.split('='))
            .reduce((acc, v) => ({ ...acc, [v[0]]: v[1] }), {});
        
        if ("a" in parsedMetadata) {
            step.action = parsedMetadata["a"];
        } 
        else throw new Error("Missing property a");

        if ("i" in parsedMetadata) {
            step.identifier = parsedMetadata["i"];
        }
        if ("l" in parsedMetadata) {
            step.location = parsedMetadata["l"]
                .substring(1, parsedMetadata["l"].length - 1)
                .split(",")
                .map(n => parseInt(n));
        }
        if ("t" in parsedMetadata) {
            step.dataType = parsedMetadata["t"];

            switch(parsedMetadata["t"]) {
                case "int":
                    step.dataValue = Module.HEAP32[dataPtr / 4];
                    break;
                default: 
                    throw new Error("Unsupported data type " + parsedMetadata["t"]);
            }
        }
        
        // Create step 
        Module.simulatorSteps = Module.simulatorSteps || [];
        Module.simulatorSteps.push(step);
    }
});