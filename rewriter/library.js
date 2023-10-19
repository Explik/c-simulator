mergeInto(LibraryManager.library, {
    notify: function(metadata, dataPtr) {
        // Parse raw data
        var getValue = (arr, name) => arr.find(i => i[0] == name) && arr.find(i => i[0] == name)[1];
        var properties = UTF8ToString(metadata).split(';').map(s => s.split('='));
        
        var dataValue;
        var dataType = getValue(properties, "t");
        switch(dataType) {
            case "int": 
                dataValue = Module.HEAP32[dataPtr / 4];
                break;
            default: 
                throw new Error("Unsupported data type " + dataType);
        }

        var rawLocation = getValue(properties, "l");
        var location = rawLocation && rawLocation.substring(1, rawLocation.length - 1).split(",").map(n => parseInt(n));
        
        // Create step 
        var simulatorStep;
        switch(getValue(properties, "a")) {
            case "assign": 
                simulatorStep = {
                    action: "assign",
                    identifier: getValue(properties, "i"),
                    dataType: dataType,
                    dataValue: dataValue
                };
                break;
            case "decl": 
                simulatorStep = {
                    action: "decl",
                    identifier: getValue(properties, "i"),
                    dataType: dataType,
                    dataValue: dataValue
                };
                break;
            case "eval": 
                simulatorStep = {
                    action: "eval",
                    location: location,
                    dataType: dataType,
                    dataValue: dataValue
                }
                break;
            default:
                throw new Error("Unsupported " + getValue(properties, "a"))
            
        }

        Module.simulatorSteps = Module.simulatorSteps || [];
        Module.simulatorSteps.push(simulatorStep);
    }
});