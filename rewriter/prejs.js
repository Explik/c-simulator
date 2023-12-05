var Module = Module || { };
Module.print = function() { 
   Module.simulatorSteps = Module.simulatorSteps || [];
   Module.simulatorSteps.push({ action: "stdout", value: Array.from(arguments).join("") + "\\n\n"});
}
Module.printErr = function() { 
   Module.simulatorSteps = Module.simulatorSteps || [];
   Module.simulatorSteps.push({ action: "stderr", value: Array.from(arguments).join("") + "\\n\n"});
}
Module.notify = function(reference, dataPointers) {
    Module.simulatorSteps = Module.simulatorSteps || [];

    var i = 0;
    var steps = [];
    var notifications = Module.simulatorNotifications.filter(n => n.ref == reference); 
    for (var notification of notifications) {
        if (["assign", "eval", "decl", "par"].includes(notification.action)) {
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
            steps.push({ ...notification, dataValue: dataValue });
            i++;
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

Module.preRun = Module.preRun || [];
Module.preRun.push(function() {
  Module.simulatorCode = {code};
  Module.simulatorNodes = {statements};
  Module.simulatorNotifications = {notifications};
});