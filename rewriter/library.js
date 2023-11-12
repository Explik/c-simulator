mergeInto(LibraryManager.library, {
    notify: function(metadataPtr, dataPtr) {
        var metadata = Module.simulatorNotifications[metadataPtr];

        // Retreive data value
        var dataType = metadata.dataType;
        var dataValue;
        switch(dataType) {
            case "int":
            case "long":
                dataValue = getValue(dataPtr, 'i32');
                break;
            default: 
                dataValue = getValue(dataPtr, dataType);
                break;
        }

        // Create step 
        Module.simulatorSteps = Module.simulatorSteps || [];
        if (Module.simulatorSteps.length < 10000) {
            Module.simulatorSteps.push({ ...metadata, dataValue: dataValue });
            console.log({ ...metadata, dataValue: dataValue });
        }
        else throw new Error("Too many steps (possible infinite loop)");
    }
});