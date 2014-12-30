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

// TODO: more docstrings
/**
 * The root of the query builder.
 *
 * Should have a spec attribute, which contains the json spec for the query
 * builder (TODO: detail the various data interchange formats somewhere)
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
    return _.union(_.map(booleanFilters, 'name'),
                   this.props.spec.filterNames);
  },

  allFilters: function () {
    return _.defaults(this.props.spec.filters,
                      _.zipObject(_.map(booleanFilters, 'name'),
                                  booleanFilters));
  },

  render: function () {
    return <div className="query-builder">
      Find {this.props.spec.englishName} with&hellip;
      <QueryNode ref="queryNode"
                 filters={this.allFilters()}
                 filterNames={this.allFilterNames()} />
      <button onClick={this.submit}>Go</button>
    </div>;
  },
});

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
    onRemove: React.PropTypes.func, // leave this out to not allow removing the node (i.e. for the root)
  },

  getInitialState: function () {
    return {
      currentFilterName: "",
      error: null,
    }
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
        'negated': this.refs.filterSelector.refs.checkbox.getDOMNode().checked,
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
      removeButton = <button onClick={this.props.onRemove} >-</button>;
    }
    return <div>
      <span className="error">{this.state.error}</span>
      <FilterSelector ref="filterSelector"
                      filterNames={this.props.filterNames}
                      filters={this.props.filters}
                      onChange={this.handleChange}
                      value={this.state.currentFilterName}/>
      {filterBody}
      {removeButton}
    </div>;
  },
});

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
    onChange: React.PropTypes.func.isRequired,
    value: React.PropTypes.string
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
      <input type="checkbox" ref="checkbox"/>
      <select onChange={this.props.onChange} value={this.props.value}>
        <option value={null}></option>
        {options}
      </select>
    </span>;
  },
});

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

var TrivialInput = React.createClass({
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
      // TODO: allow optional fields
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
      <select ref="select">
        <option value={null}></option>
        {options}
      </select>
    </span>;
  },
});

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
    this.setState({
      show: !this.state.show,
    });
  },

  render: function () {
    var inner = null;
    var name = this.props.input.name;
    if (this.state.show) {
      var innerClass = window[this.props.input.inner.reactClass];
      inner = <innerClass ref="inner" input={this.props.input.inner} />;
      name.replace(/show/, "hide")
    }
    return <span>
      <button onClick={this.handleClick}>{this.props.input.name}</button>
      {inner}
    </span>;
  },
});

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
      <select ref="comparison" defaultValue="before">
        <option>before</option>
        <option>after</option>
        <option>exactly</option>
      </select>
      <input type="text" className="datetime-input" ref="datetime" />
    </span>;
  },
});

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
    // TODO: if two of these updates get batched, the second one will get eaten
    // by React.  This is probably okay if you don't click the add button too
    // fast.
  },

  handleRemove: function (key) {
    // TODO: same issue as handleAdd.
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
      <ul>
        {children}
        <li><button onClick={this.handleAdd}>+</button></li>
      </ul>
    </div>;
  },
});
