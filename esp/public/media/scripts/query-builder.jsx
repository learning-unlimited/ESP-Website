/** @jsx React.DOM */

var booleanFilters = [
  {
    "name": "and",
    "title": "all of...",
  },
  {
    "name": "or",
    "title": "any of...",
  },
]

function BuildQueryError() {
    this.name = "BuildQueryError";
}

/**
 * The root of the query builder.
 *
 * Props:
 *   `spec`: A specification describing the query builder.  This should have
 *   the following keys:
 *     `englishName`: the name of the thing being queried.
 *     `filterNames`: a list of the internal names of the possible filters.
 *     `filters`: an object with the elements of `filterNames` as keys.  The
 *       values should be objects describing the filters.  They should have
 *       the following keys:
 *         `name`: the same as the name from `filterNames`
 *         `title`: a human-readable name for the filter
 *         `inputs`: an array of input objects, describing each input to the
 *           filter.  Each must have a key `reactClass` which should be the
 *           name of the React class that displays the input.  They may also
 *           have more keys as specified by that class.
 *
 * Note that the boolean operations `and` and `or` need not be included in the
 * list of filters.
 *
 * Each input React class must have a single Prop, `input`, which takes an
 * object as described under `input` above.  In addition to the usual React
 * methods, it must have a method `asJSON` which returns a value that will be
 * passed through to the corresponding python class to be interpreted.  The
 * method may alternately raise a BuildQueryError if the user's input is
 * invalid, in which case it should show the invalid input.
 *
 * When the submit button is pressed, this generates a JSON object representing
 * the query, and sends it to the current URL as the GET parameter `query`.
 * The JSON is an object with the following keys:
 *   `filter`: the name of the filter (or boolean operation).
 *   `negated`: a boolean, true if the filter was negated.
 *   `values`: an array of the values of the inputs in the filter.  These
 *     objects are described in the documentation of each input class.  For
 *     boolean operations, these will be other objects with the same structure
 *     as the root.
 */
var QueryBuilder = React.createClass({
  propTypes: {
    spec: React.PropTypes.shape({
      englishName: React.PropTypes.string.isRequired,
      filterNames: React.PropTypes.arrayOf(React.PropTypes.string).isRequired,
      filters: React.PropTypes.objectOf(React.PropTypes.shape({
        name: React.PropTypes.string.isRequired,
        title: React.PropTypes.string.isRequired,
        inputs: React.PropTypes.arrayOf(React.PropTypes.shape({
          reactClass: React.PropTypes.string.isRequired,
        })).isRequired,
      })).isRequired,
    }).isRequired,
  },

  asJSON: function () {
    return this.refs.queryNode.asJSON();
  },

  /**
   * Handler to submit the query.
   */
  submit: function () {
    try {
      json = JSON.stringify(this.asJSON());
      window.location.href = "?query=" + encodeURIComponent(json);
    } catch (e) {
      if (e.name != "BuildQueryError") {
        alert("There was an error, recheck your query or poke web support.");
        // If we didn't raise the error, rethrow it.
        throw e;
      } else {
        alert("Your query contained an error.");
        return;
      }
    }
  },

  allFilterNames: function () {
    return _.union(this.props.spec.filterNames, _.map(booleanFilters, 'name'));
  },

  allFilters: function () {
    return _.defaults(this.props.spec.filters,
                      _.zipObject(_.map(booleanFilters, 'name'),
                                  booleanFilters));
  },

  render: function () {
    return <div className="query-builder">
      Find {this.props.spec.englishName}&hellip;
      <QueryNode ref="queryNode"
                 filters={this.allFilters()}
                 filterNames={this.allFilterNames()} />
      <button onClick={this.submit} className="qb-input btn btn-primary">
        Go
      </button>
    </div>;
  },
});

/**
 * A single node of the query builder, containing a single filter or boolean
 * operation.
 */
var QueryNode = React.createClass({
  propTypes: {
    filterNames: React.PropTypes.arrayOf(React.PropTypes.string).isRequired,
    filters: React.PropTypes.objectOf(React.PropTypes.shape({
      name: React.PropTypes.string.isRequired,
      title: React.PropTypes.string.isRequired,
      inputs: React.PropTypes.arrayOf(React.PropTypes.shape({
        reactClass: React.PropTypes.string.isRequired,
      })),
    })).isRequired,
    // A handler to call if the node is removed.  Leave out onRemove to not
    // allow removing the node (e.g. for the root).
    onRemove: React.PropTypes.func,
  },

  getInitialState: function () {
    return {
      currentFilterName: "",
      error: null,
      negated: false,
    }
  },

  handleToggle: function (event) {
    this.setState({negated: event.target.value == "without"});
  },

  handleChange: function (event) {
    this.setState({currentFilterName: event.target.value});
  },

  asJSON: function () {
    if (!this.state.currentFilterName) {
      this.setState({error: "select a filter!"});
      throw new BuildQueryError();
    } else {
      this.setState({error: null});
      return {
        'filter': this.state.currentFilterName,
        'negated': this.state.negated,
        'values': this.refs.filter.asJSON(),
      };
    }
  },

  render: function () {
    var filterBody = null;
    if (this.state.currentFilterName) {
      if (_.some(booleanFilters, {'name': this.state.currentFilterName})) {
        filterBody = <BooleanOp ref="filter"
                                op={this.state.currentFilterName}
                                filterNames={this.props.filterNames}
                                filters={this.props.filters} />;
      } else {
        var currentFilter = this.props.filters[this.state.currentFilterName];
        filterBody = <Filter ref="filter" filter={currentFilter} />;
      }
    }
    var removeButton = null;
    if (this.props.onRemove) {
      removeButton = <button onClick={this.props.onRemove}
                             className="qb-input btn btn-default">
        -
      </button>;
    }
    return <div>
      {removeButton}
      <span className="error">{this.state.error}</span>
      <FilterSelector filterNames={this.props.filterNames}
                      filters={this.props.filters}
                      onChange={this.handleChange}
                      value={this.state.currentFilterName}
                      onToggle={this.handleToggle}
                      negated={this.state.negated} />
      {filterBody}
    </div>;
  },
});

/**
 * The drop-down to select a filter, and button to possibly negate it.
 */
var FilterSelector = React.createClass({
  propTypes: {
    filterNames: React.PropTypes.arrayOf(React.PropTypes.string).isRequired,
    filters: React.PropTypes.objectOf(React.PropTypes.shape({
      name: React.PropTypes.string.isRequired,
      title: React.PropTypes.string.isRequired,
      inputs: React.PropTypes.arrayOf(React.PropTypes.shape({
        reactClass: React.PropTypes.string.isRequired,
      })),
    })).isRequired,
    // The callback for when the filter is changed.
    onChange: React.PropTypes.func.isRequired,
    // The current chosen filter.
    value: React.PropTypes.string,
    // The callback to toggle negation.
    onToggle: React.PropTypes.func.isRequired,
    // Are we negated?
    negated: React.PropTypes.bool.isRequired,
  },

  render: function () {
    var options = _.map(
      this.props.filterNames,
      function (filterName) {
        var filter = this.props.filters[filterName];
        return <option key={filterName} value={filterName}>
          {filter.title}
        </option>;
      }.bind(this));
    return <span>
      <select onChange={this.props.onToggle}
              value={this.props.negated ? "without" : "with"}
              className="qb-input qb-negate"
              >
        <option value="with">with</option>
        <option value="without">without</option>
      </select>
      <select onChange={this.props.onChange} value={this.props.value}
              className="qb-input">
        <option value={null}></option>
        {options}
      </select>
    </span>;
  },
});

/**
 * The body of a filter.
 */
var Filter = React.createClass({
  propTypes: {
    filter: React.PropTypes.shape({
      name: React.PropTypes.string.isRequired,
      title: React.PropTypes.string.isRequired,
      inputs: React.PropTypes.arrayOf(React.PropTypes.shape({
        reactClass: React.PropTypes.string.isRequired,
      })),
    }).isRequired,
  },

  asJSON: function () {
    return _.map(this.props.filter.inputs,
                 function (input, i) {
                   return this.refs[i].asJSON();
                 }.bind(this));
  },

  render: function () {
    var inputs = _.map(this.props.filter.inputs,
                       function (input, i) {
                         // We need to get the class with the name that is the
                         // string input.reactClass.  Doing so is
                         // *terrifyingly* easy.
                         var inputClass = window[input.reactClass];
                         return <inputClass ref={i} key={i} input={input} />;
                       });
    return <span>
      {inputs}
    </span>;
  },
});

/**
 * An input which adds a fixed Q object to the filter.
 *
 * The output JSON data is null.
 */
var ConstantInput = React.createClass({
  propTypes: {
    input: React.PropTypes.shape({
      reactClass: React.PropTypes.string.isRequired,
    }).isRequired,
  },

  asJSON: function () {
    return null;
  },

  render: function () {
    return null;
  },
});

/**
 * An input reperesented by an HTML <select> with a fixed set of options.
 *
 * The input specification object should have the following extra key:
 *   `options`: an array of objects, each of which has the following keys:
 *     `name`: a string or number representing the option.  Note: this may get
 *       coerced to a string by Javascript.
 *     `title`: the human-readable description of the option.
 *
 * The output JSON data is the `name` of the chosen option.
 */
var SelectInput = React.createClass({
  propTypes: {
    input: React.PropTypes.shape({
      reactClass: React.PropTypes.string.isRequired,
      options: React.PropTypes.arrayOf(React.PropTypes.shape({
        name: React.PropTypes.oneOfType([
          React.PropTypes.string,
          React.PropTypes.number,
        ]).isRequired,
        title: React.PropTypes.string.isRequired,
      })).isRequired,
    }).isRequired,
  },

  getInitialState: function () {
    return {error: null};
  },

  asJSON: function () {
    var val = this.refs.select.getDOMNode().value;
    if (val == "") {
      this.setState({error: "Select an option!"});
      throw new BuildQueryError();
    } else {
      this.setState({error: null});
      return val;
    }
  },

  render: function () {
    var options = _.map(this.props.input.options,
                        function (option) {
                          return <option key={option.name} value={option.name}>
                            {option.title}
                          </option>;
                        });
    return <span>
      <span className="error">{this.state.error}</span>
      <select ref="select" className="qb-input">
        <option value={null}></option>
        {options}
      </select>
    </span>;
  },
});

/**
 * An input that can either use or not use another input.
 *
 * The input specification object should have the following additional keys:
 *   `name`: the name of the optional input, to go on the button.  When the
 *     input is shown, the word "show" in `name` will be changed to "hide".
 *   `inner`: another input specification object, for the input which might be
 *     used.
 * 
 * The output JSON data is null if the input was not used, and the value of the
 * input otherwise.
 */
var OptionalInput = React.createClass({
  propTypes: {
    input: React.PropTypes.shape({
      reactClass: React.PropTypes.string.isRequired,
      name: React.PropTypes.string.isRequired,
      inner: React.PropTypes.shape({
        reactClass: React.PropTypes.string.isRequired,
      }).isRequired,
    }).isRequired,
  },

  getInitialState: function () {
    return {show: false};
  },

  asJSON: function () {
    if (this.state.show) {
      return this.refs.inner.asJSON();
    } else {
      return null;
    }
  },

  handleClick: function () {
    this.setState({show: !this.state.show});
  },

  render: function () {
    var inner = null;
    buttonClasses="qb-optional-button qb-input btn "
    if (this.state.show) {
      var innerClass = window[this.props.input.inner.reactClass];
      inner = <innerClass ref="inner" input={this.props.input.inner} />;
      buttonClasses = buttonClasses + "active btn-success"
    } else {
      buttonClasses = buttonClasses + "btn-default"
    }
    return <div>
      <button onClick={this.handleClick} className={buttonClasses}>
        {this.props.input.name}
      </button>
      {inner}
    </div>;
  },
});

/**
 * An input for before, after, or exactly at a datetime.
 *
 * The input specification object should have the following additional key:
 *   `name`: the human-readable name describing the datetime.
 *
 * The output JSON data is an object with the following keys:
 *   `comparison`: "before", "after", or "exactly".
 *   `datetime`: the datetime in "%m/%d/%Y %H:%M" format.
 */
var DatetimeInput = React.createClass({
  propTypes: {
    input: React.PropTypes.shape({
      reactClass: React.PropTypes.string.isRequired,
      name: React.PropTypes.string.isRequired,
    }).isRequired,
  },

  asJSON: function () {
    return {
      comparison: this.refs.comparison.getDOMNode().value,
      datetime: this.refs.datetime.getDOMNode().value,
    };
  },

  componentDidMount: function () {
    this.componentDidUpdate();
  },

  componentDidUpdate: function () {
    $j(this.refs.datetime.getDOMNode()).datetimepicker();
  },

  render: function () {
    return <span>
      {this.props.input.name}
      <select ref="comparison" defaultValue="before"
              className="qb-input qb-datetime-select">
        <option>before</option>
        <option>after</option>
        <option>exactly</option>
      </select>
      <input type="text" className="datetime-input qb-input" ref="datetime" />
    </span>;
  },
});

/**
 * An input for arbitrary text.
 *
 * The input specification object may have the following additional key:
 *   `name`: the human-readable name describing the text (optional)
 *
 * The output JSON data is the text entered.
 */
var TextInput = React.createClass({
  propTypes: {
    input: React.PropTypes.shape({
      reactClass: React.PropTypes.string.isRequired,
      name: React.PropTypes.string,
    }).isRequired,
  },

  asJSON: function () {
    return this.refs.input.getDOMNode().value;
  },

  render: function () {
    return <span>
      {this.props.input.name}
      <input type="text" ref="input" className="qb-input" />
    </span>;
  },
});

/**
 * A boolean operation.
 *
 * In addition to the filter specification to be passed around, BooleanOp takes
 * the following additional Prop:
 *   `op`: either "and" or "or".
 */
var BooleanOp = React.createClass({
  propTypes: {
    op: React.PropTypes.string.isRequired,
    filterNames: React.PropTypes.arrayOf(React.PropTypes.string).isRequired,
    filters: React.PropTypes.objectOf(React.PropTypes.shape({
      name: React.PropTypes.string.isRequired,
      title: React.PropTypes.string.isRequired,
      inputs: React.PropTypes.arrayOf(React.PropTypes.shape({
        reactClass: React.PropTypes.string.isRequired,
      })),
    })).isRequired,
  },

  getNewChild: function (key) {
    return <QueryNode key={key}
                      filterNames={this.props.filterNames}
                      filters={this.props.filters} />;
  },

  getInitialState: function () {
    return {
      // Each child filter gets assigned a unique ID, so we and React can keep
      // track of it.  this.state.childKeys contains the current set of such
      // keys in use.
      childKeys: [_.uniqueId()],
      error: null,
    };
  },

  asJSON: function () {
    if (!this.state.childKeys.length) {
      this.setState({error: "No subqueries specified"});
      throw new BuildQueryError();
    } else {
      this.setState({error: null});
      return _.map(this.state.childKeys,
                   function (key) {
                     return this.refs[key].asJSON();
                   }.bind(this));
    }
  },

  handleAdd: function () {
    // Copy, because this.state should be treated as immutable
    var childKeys = this.state.childKeys.slice(0);
    childKeys.push(_.uniqueId())
    this.setState({
      childKeys: childKeys,
    });
  },

  handleRemove: function (key) {
    this.setState({
      childKeys: _.without(this.state.childKeys, key),
    });
  },

  render: function () {
    var children = _.map(this.state.childKeys,
                         function (key) {
                           return <li key={key}>
                             <QueryNode ref={key}
                                        onRemove={this.handleRemove.bind(this, key)}
                                        filterNames={this.props.filterNames}
                                        filters={this.props.filters} />
                           </li>;
                         }.bind(this));
    return <div>
      <span className="error">{this.state.error}</span>
      <ul className="qb-ul">
        {children}
        <li>
          <button onClick={this.handleAdd}
                  className="qb-input btn btn-default">
            +
          </button>
        </li>
      </ul>
    </div>;
  },
});
