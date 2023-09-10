mergeInto(LibraryManager.library, {
    notify: function(metadata, dataPtr) {
        // For the purpose of this example, I'm assuming `data` is an integer
        var metadataValue = UTF8ToString(metadata);
        var dataValue = Module.HEAP32[dataPtr / 4];
        console.log(`Metadata: ${metadataValue}, Value: ${dataValue}`);

        var parsedMetadata = metadataValue.split(';').map(s => s.split('='))
        var parsedType = parsedMetadata.find(s => s[0] === 't')[1];
        var parsedLocation = JSON.parse(parsedMetadata.find(s => s[0] === 'l')[1]);
        
        window.codeChanges = window.codeChanges || [];
        window.codeChanges.push({ location: parsedLocation, code: dataValue })
    }
});