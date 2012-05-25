/**
 * @private
 */
Ext.define('Ext.slider.Toggle', {
    extend: 'Ext.slider.Slider',

    config: {
        /**
         * @cfg
         * @inheritdoc
         */
        baseCls: 'x-toggle',

        /**
         * @cfg {String} minValueCls CSS class added to the field when toggled to its minValue
         * @accessor
         */
        minValueCls: 'x-toggle-off',

        /**
         * @cfg {String} maxValueCls CSS class added to the field when toggled to its maxValue
         * @accessor
         */
        maxValueCls: 'x-toggle-on'
    },

    initialize: function() {
        this.callParent();

        this.on({
            change: 'onChange'
        });
    },

    applyMinValue: function() {
        return 0;
    },

    applyMaxValue: function() {
        return 1;
    },

    applyIncrement: function() {
        return 1;
    },

    setValue: function(newValue, oldValue) {
        this.callParent(arguments);
        this.onChange(this, this.getThumbs()[0], newValue, oldValue);
    },

    onChange: function(me, thumb, newValue, oldValue) {
        var isOn = newValue > 0,
            onCls = me.getMaxValueCls(),
            offCls = me.getMinValueCls();

        this.element.addCls(isOn ? onCls : offCls);
        this.element.removeCls(isOn ? offCls : onCls);
    }
});
