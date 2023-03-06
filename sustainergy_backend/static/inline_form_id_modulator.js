console.log(django.jQuery);
(function($) {
  var api_url = '/new_model_id/';


    $(document).on('formset:added', function(event, $row, formsetName) {
      if (formsetName == "building_set") {
        var id_inputs = $row[0].getElementsByClassName("idbuildings")[0].getElementsByTagName("input");
        jQuery.ajax({
          method: 'GET',
          url: api_url + "building/"
        }).done(function(data) {
          if (data != "error") {
            for (let i = 0; i < id_inputs.length; i++) {
            id_inputs[i].value = data;
          }
          }
        })
      } else if (formsetName == "panel_set") {
        var id_inputs = $row[0].getElementsByClassName("panel_id")[0].getElementsByTagName("input");
        jQuery.ajax({
          method: 'GET',
          url: api_url + 'panel/'
        }).done(function(data) {
          if (data != "error") {
            for (let i = 0; i < id_inputs.length; i++) {
              id_inputs[i].value = data;
            }
          }
        })
      } else if (formsetName == "circuit_set") {
        console.log("Circuit set found");
      }
    });

  /*
    $(document).on('formset:removed', function(event, $row, formsetName) {
      console.log("Formset Removed");
      console.log(event);
      console.log($row);
      console.log(formsetName);
    });
  */
})(django.jQuery);
