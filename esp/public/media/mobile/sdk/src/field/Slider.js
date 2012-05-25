/**
 * @aside guide forms
 *
 * The slider is a way to allow the user to select a value from a given numerical range. You might use it for choosing
 * a percentage, combine two of them to get min and max values, or use three of them to specify the hex values for a
 * color. Each slider contains a single 'thumb' that can be dragged along the slider's length to change the value.
 * Sliders are equally useful inside {@link Ext.form.Panel forms} and standalone. Here's how to quickly create a
 * slider in form, in this case enabling a user to choose a percentage:
 *
 *     @example
 *     Ext.create('Ext.form.Panel', {
 *         fullscreen: true,
 *         items: [
 *             {
 *                 xtype: 'sliderfield',
 *                 label: 'Percentage',
 *                 value: 50,
 *                 minValue: 0,
 *                 maxValue: 100
 *             }
 *         ]
 *     });
 *
 * In this case we set a starting value of 50%, and defined the min and max values to be 0 and 100 respectively, giving
 * us a percentage slider. Because this is such a common use case, the defaults for {@link #minValue} and
 * {@link #maxValue} are already set to 0 and 100 so in the example above they could be removed.
 *
 * It's often useful to render sliders outside the context of a form panel too. In this example we create a slider that
 * allows a user to choose the waist measurement of a pair of jeans. Let's say the online store we're making this for
 * sells jeans with waist sizes from 24 inches to 60 inches in 2 inch increments - here's how we might achieve that:
 *
 *     @example
 *     Ext.create('Ext.form.Panel', {
 *         fullscreen: true,
 *         items: [
 *             {
 *                 xtype: 'sliderfield',
 *                 label: 'Waist Measurement',
 *                 minValue: 24,
 *                 maxValue: 60,
 *                 increment: 2,
 *                 value: 32
 *             }
 *         ]
 *     });
 *
 * Now that we've got our slider, we can ask it what value it currently has and listen to events that it fires. For
 * example, if we wanted our app to show different images for different sizes, we can listen to the {@link #change}
 * event to be informed whenever the slider is moved:
 *
 *     slider.on('change', function(field, newValue) {
 *         if (newValue[0] > 40) {
 *             imgComponent.setSrc('large.png')
 *         } else {
 *             imgComponent.setSrc('small.png');
 *         }
 *     }, this);
 *
 * Here we listened to the {@link #change} event on the slider and updated the background image of an
 * {@link Ext.Img image component} based on what size the user selected. Of course, you can use any logic inside your
 * event listener.
 */
Ext.define('Ext.field.Slider', {
    extend  : 'Ext.field.Field',
    xtype   : 'sliderfield',
    requires: ['Ext.slider.Slider'],
    alternateClassName: 'Ext.form.Slider',

    /**
     * @event change
     * Fires when an option selection has changed.
     * @param {Ext.field.Slider} me
     * @param {Ext.slider.Thumb} thumb
     * @param {Number} newValue the new value of this thumb
     * @param {Number} oldValue the old value of this thumb
     */

    config: {
        /**
         * @cfg
         * @inheritdoc
         */
        cls: Ext.baseCSSPrefix + 'slider-field',

        /**
         * @cfg
         * @inheritdoc
         */
        tabIndex: -1
    },

    proxyConfig: {
        /**
         * @cfg {Number/Number[]} value See {@link Ext.slider.Slider#value}
         * @accessor
         */
        value: 0,

        /**
         * @cfg {Number} minValue See {@link Ext.slider.Slider#minValue}
         * @accessor
         */
        minValue: 0,

        /**
         * @cfg {Number} maxValue See {@link Ext.slider.Slider#maxValue}
         * @accessor
         */
        maxValue: 100,

        /**
         * @cfg {Number} increment See {@link Ext.slider.Slider#increment}
         * @accessor
         */
        increment: 1
    },

    /**
     * @cfg {Number/Number[]} values See {@link Ext.slider.Slider#values}
     */

    constructor: function(config) {
        config = config || {};

        if (config.hasOwnProperty('values')) {
            config.value = config.values;
        }

        this.callParent([config]);
    },

    // @private
    initialize: function() {
        this.callParent();

        this.getComponent().on({
            scope: this,
            change: 'onSliderChange'
        });
    },

    // @private
    applyComponent: function(config) {
        return Ext.factory(config, Ext.slider.Slider);
    },

    onSliderChange: function(me, thumb, newValue, oldValue) {
        this.fireEvent('change', this, thumb, newValue, oldValue);
    },

    /**
     * Convience method. Calls {@link #setValue}
     */
    setValues: function(value) {
        this.setValue(value);
    },

    /**
     * Convience method. Calls {@link #getValue}
     */
    getValues: function() {
        return this.getValue();
    },

    reset: function() {
        var config = this.config,
            initialValue = (this.config.hasOwnProperty('values')) ? config.values : config.value;

        this.setValue(initialValue);
    },

    doSetDisabled: function(disabled) {
        this.callParent(arguments);

        this.getComponent().setDisabled(disabled);
    }
});
