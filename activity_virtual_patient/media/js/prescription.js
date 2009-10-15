function debug(string)
{
   if (true)
      log("DEBUG " + string)
}

function onXHRSuccess(response)
{
   doc = JSON.parse(response.responseText, null)
   window.location = doc.redirect 
}

function onXHRError(err)
{
}

function gotoPrescribeOrResults()
{
   url = 'http://' + location.hostname + ':' + location.port + "/activity/virtualpatient/prescription/post/"
   
   jsontxt = get_state()
      
   deferred = doXHR(url,
         { 
            method: 'POST', 
            sendContent: queryString({'json': jsontxt})
         });
   deferred.addCallbacks(onXHRSuccess, onXHRError);
}

function get_state()
{
   debug("get_state")
   
   doc = {}
   doc['patient_id'] = $('patient_id').value
   doc['medication_idx'] = $('medication_idx').value
   
   tag = $('medication_tag').value
   doc['medication_tag'] = tag
   doc[tag] = {}
   doc[tag]['concentration'] = $('concentration').options[$('concentration').selectedIndex].value
   doc[tag]['dosage'] = $('dosage').options[$('dosage').selectedIndex].value
   if ($('refill'))
      doc[tag]['refill'] = $('refill').options[$('refill').selectedIndex].value

   jsontxt = JSON.stringify(doc, null)
   return jsontxt   
}