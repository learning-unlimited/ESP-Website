//Formset settings
//For line items
$j('.option-formset').formset({
    prefix: 'options',
    formTemplate: '#id_empty_form',
    addText: 'add option',
    deleteText: 'remove',
    addCssClass: 'option-add',
    deleteCssClass: 'option-delete',
    formCssClass: 'option-dynamic-form',
});
