mergeInto(LibraryManager.library, {
    notify_0: function(reference) {
        Module.simulatorSteps = Module.simulatorSteps || [];

        var notifyNotifications = Module.simulatorNotifications.filter(n => n.ref == reference); 
        var notifySteps = notifyNotifications;

        if (Module.simulatorSteps.length > 10000)
            throw new Error("Too many steps (possible infinite loop)");

        for (step of notifySteps) {
            Module.simulatorSteps.push(step);
            console.log(step);
        }
    },
    notify_1: function(reference, ...dataPointers) {
        Module.simulatorSteps = Module.simulatorSteps || [];

        var notifyNotifications = Module.simulatorNotifications.filter(n => n.ref == reference); 
        var notifyDataNotifications = notifyNotifications.filter(n => ["assign", "eval", "decl", "par"].includes(n.action));
        var notifySteps = [];
        
        for(var i = 0; i < notifyDataNotifications.length; i++) {
            var notification = notifyDataNotifications[i];
            var dataType = notification.dataType;
            var dataValue;
            switch(dataType) {
                case "int":
                case "long":
                    dataValue = getValue(dataPointers[i], 'i32');
                    break;
                default: 
                    dataValue = getValue(dataPointers[i], dataType);
                    break;
            }
            notifySteps.push({ ...notification, dataValue: dataValue })
        }

        if (Module.simulatorSteps.length > 10000)
            throw new Error("Too many steps (possible infinite loop)");

        for (step of notifySteps) {
            Module.simulatorSteps.push(step);
            console.log(step);
        }
    },
    notify_2: function(reference, ...dataPointers) {
        Module.simulatorSteps = Module.simulatorSteps || [];

        var notifyNotifications = Module.simulatorNotifications.filter(n => n.ref == reference); 
        var notifyDataNotifications = notifyNotifications.filter(n => ["assign", "eval", "decl", "par"].includes(n.action));
        var notifySteps = [];
        
        for(var i = 0; i < notifyDataNotifications.length; i++) {
            var notification = notifyDataNotifications[i];
            var dataType = notification.dataType;
            var dataValue;
            switch(dataType) {
                case "int":
                case "long":
                    dataValue = getValue(dataPointers[i], 'i32');
                    break;
                default: 
                    dataValue = getValue(dataPointers[i], dataType);
                    break;
            }
            notifySteps.push({ ...notification, dataValue: dataValue })
        }

        if (Module.simulatorSteps.length > 10000)
            throw new Error("Too many steps (possible infinite loop)");

        for (step of notifySteps) {
            Module.simulatorSteps.push(step);
            console.log(step);
        }
    },
    notify_3: function(reference, ...dataPointers) {
        Module.simulatorSteps = Module.simulatorSteps || [];

        var notifyNotifications = Module.simulatorNotifications.filter(n => n.ref == reference); 
        var notifyDataNotifications = notifyNotifications.filter(n => ["assign", "eval", "decl", "par"].includes(n.action));
        var notifySteps = [];
        
        for(var i = 0; i < notifyDataNotifications.length; i++) {
            var notification = notifyDataNotifications[i];
            var dataType = notification.dataType;
            var dataValue;
            switch(dataType) {
                case "int":
                case "long":
                    dataValue = getValue(dataPointers[i], 'i32');
                    break;
                default: 
                    dataValue = getValue(dataPointers[i], dataType);
                    break;
            }
            notifySteps.push({ ...notification, dataValue: dataValue })
        }

        if (Module.simulatorSteps.length > 10000)
            throw new Error("Too many steps (possible infinite loop)");

        for (step of notifySteps) {
            Module.simulatorSteps.push(step);
            console.log(step);
        }
    },
    notify: function(reference, dataPointers) {
        Module.simulatorSteps = Module.simulatorSteps || [];

        var notifyNotifications = Module.simulatorNotifications.filter(n => n.ref == reference); 
        var notifyDataNotifications = notifyNotifications.filter(n => ["assign", "eval", "decl", "par"].includes(n.action));
        var notifySteps = [];
        
        for(var i = 0; i < notifyDataNotifications.length; i++) {
            var notification = notifyDataNotifications[i];
            var dataType = notification.dataType;
            var dataValue;
            switch(dataType) {
                case "int":
                case "long":
                    dataValue = getValue(dataPointers[i], 'i32');
                    break;
                default: 
                    dataValue = getValue(dataPointers[i], dataType);
                    break;
            }
            notifySteps.push({ ...notification, dataValue: dataValue })
        }

        if (Module.simulatorSteps.length > 10000)
            throw new Error("Too many steps (possible infinite loop)");

        for (step of notifySteps) {
            Module.simulatorSteps.push(step);
            console.log(step);
        }
    }
});