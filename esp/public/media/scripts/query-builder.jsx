/** @jsx React.DOM */

var booleanFilters = [
  {
    "name": "and",
    "title": "all of the following...",
  },
  {
    "name": "or",
    "title": "some of the following...",
  },
]

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

  asJson: function () {
    // TODO
  },

  submit: function () {
    // TODO
  },

  allFilterNames: function () {
    return _.union(this.props.spec.filterNames,
                   _.map(booleanFilters, 'name'));
  },

  allFilters: function () {
    return _.defaults(this.props.spec.filters,
                      _.zipObject(_.map(booleanFilters, 'name'),
                                  booleanFilters));
  },

  render: function () {
    return <div className="query-builder">
      Find {this.props.spec.englishName} with&hellip;
      <QueryNode filters={this.allFilters()}
                 filterNames={this.allFilterNames()} />
      // TODO: submit button
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
      currentFilterName: null,
    }
  },

  handleChange: function (event) {
    this.setState({currentFilterName: event.target.value});
  },

  render: function () {
    var filterBody = null;
    if (this.state.currentFilterName) {
      if (_.some(booleanFilters, {'name': this.state.currentFilterName})) {
        filterBody = <BooleanOp op={this.state.currentFilterName}
                                filterNames={this.props.filterNames}
                                filters={this.props.filters} />;
      } else {
        var currentFilterSpec = this.props.filters[this.state.currentFilterName];
        filterBody = <Filter filter={currentFilterSpec} />;
      }
    }
    var removeButton = null;
    if (this.props.onRemove) {
      removeButton = <button onClick={this.props.onRemove} >-</button>;
    }
    return <div>
      <FilterSelector filterNames={this.props.filterNames}
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
      <input type="checkbox" />
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

  render: function () {
    var inputs = _.map(this.props.filter.inputs,
                       function (input, i) {
                         // We need to get the class with the name that is the
                         // string input.reactClass.  Doing so is
                         // *terrifyingly* easy.
                         var inputClass = window[input.reactClass];
                         return <inputClass key={i} input={input} />;
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

  render: function () {
    var options = _.map(this.props.input.options,
                        function (option) {
                          console.log(option);
                          return <option key={option.name} name={option.name}>
                            {option.title}
                          </option>;
                        });
    return <select>
      <option value={null}></option>
      {options}
    </select>;
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
    };
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
                             <QueryNode onRemove={this.handleRemove.bind(this, key)}
                                        filterNames={this.props.filterNames}
                                        filters={this.props.filters} />
                           </li>;
                         }.bind(this));
    return <ul>
      {children}
      <li><button onClick={this.handleAdd}>+</button></li>
    </ul>;
  },
});
