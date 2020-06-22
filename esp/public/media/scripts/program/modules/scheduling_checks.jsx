/**
 * List of scheduling checks.
 *
 * Should have individual SchedulingCheck elements as children.
 */
var SchedulingCheckList = React.createClass({
  render: function () {
    return <div className="scheduling-check-list">
      {this.props.children}
    </div>;
  },
});

/**
 * A single scheduling check.
 *
 * This might or might not be loaded yet; clicking the heading will load the
 * data from the server and expand it.
 * 
 * There is supposedly a functionality in which clicking on a table row will cause it
 * to be greyed out, however whether this actually happens depends on your
 * scheduling_checks.css (clicking could possibly do nothing, or possibly
 * do other things).
 *
 * Likewise, clicking on a table header will sort by that column. You can also
 * add formatting in scheduling_checks.css so that the selected header will
 * look different, e.g. be colored differently.
 */
var SchedulingCheck = React.createClass({
  propTypes: {
    slug: React.PropTypes.string.isRequired,
    title: React.PropTypes.string,
  },

  getInitialState: function () {
    return {
      open: false,
      failed: false,
      timestamp: "never",
      tableState: {
        greyed: {},
        sort: -1,
        reverse: false
      },
    };
  },
  
  sortColumn: function (column) {
    if (this.state.tableState.sort === column) {
      this.setState( {
        tableState: React.addons.update(this.state.tableState, 
          { reverse: {$set: !this.state.tableState.reverse} } ),
        } );   
    } else {
      this.setState( {
        tableState: React.addons.update(this.state.tableState, { sort: {$set: column}, reverse: {$set: false} }),
        } );
    }
  },
  
  greyRow: function(item ){
    newkey = {};
    newkey[item] = !this.state.tableState.greyed[item];
    this.setState( {
      tableState: React.addons.update(this.state.tableState, { greyed: {$merge: newkey} } ),
      } );
  },
  
  resetTable: function () {
    this.setState({
      tableState: {
        greyed: {},
        sort: -1,
        reverse: false
      },
      });
    
  },

  handleClick: function () {
    if (this.state.open) {
      this.setState({open: false})
    } else {
      this.setState({open: true});
      if (!this.state.data) {
        this.loadData();
      }
    }
  },

  timestamp: function () {
      var now = new Date();
      return now.toLocaleTimeString();
  },

  loadData: function () {
    // remove any existing data, so we see a loading thing again
    this.setState({data: undefined});
    this.setState({timestamp: "loading"});

    $j.get("scheduling_checks/" + this.props.slug)
    .done(function (data) {
      this.setState({
        data: data,
        failed: false,
        timestamp: this.timestamp(),
      });
    }.bind(this))  
    .fail(function (data) {
      this.setState({
        failed: true,
        timestamp: this.timestamp(),
      });
    }.bind(this));
  },

/*loads all of the scheduling checks */
  componentDidMount() {
    this.loadData();
  },

  render: function () {
    var body;
    if (this.state.failed) {
      body = <div className="placeholder load_fail">
        (loaded {this.state.timestamp}, loading failed ☹)
      </div>;
    } else if (!this.state.open && this.state.timestamp =="never") {
      body = <div className="placeholder load_fail">
        (loaded {this.state.timestamp})
      </div>;
    }else if (this.state.timestamp == "loading") {
      body = <div className="placeholder load_yellow">loading...</div>;
    }else if (!this.state.open) {
      body = <div className="placeholder load_ready">
        (loaded {this.state.timestamp})
      </div>;
    }else if (!this.state.data) {
      body = <div className="placeholder load_yellow">loading...</div>;
    } else {
      var data = JSON.parse(this.state.data); // Might not work on old browsers
      var table;
      if (data.headings.length == 0) {
        table = <SelectTable rows = {data.body} header = {false} 
                  saveState = {this.state.tableState} 
                  clickHeader = {this.sortColumn} clickRow = {this.greyRow} 
                  />;
      } else {
        var columns = [];
        for (i = 0; i < data.headings.length; i++) {
          if (data.headings[i]) {
            columns[i] = {key: String(i), label: data.headings[i]};
          } else {
            columns[i] = {key: String(i), label: "Date/Time"};
          }
        }
        table = <SelectTable rows = {data.body} columns = {columns} 
                  header = {true} saveState = {this.state.tableState} 
                  clickHeader = {this.sortColumn} clickRow = {this.greyRow} 
                  />;
      }
      var helpText;
      if (data.help_text) {
        helpText = <div className="help-text">{data.help_text}</div>;
      }
      body = <div>
        <div className="placeholder load_ready">
          (loaded {this.state.timestamp})
        </div>
        <div className="alittlepspace"></div>
        {helpText}
        {table}
      </div>;
    }

    return <div className="scheduling-check">
      <div className="scheduling-check-title">
        <span onClick={this.handleClick}>{this.props.title}</span>
        <ScheduleButton onClick={this.handleClick} />
        <RefreshButton onClick={this.loadData} />
        <ResetButton onClick={this.resetTable} />
      </div>
      <div className="scheduling-check-body">
        {body}
      </div>
    </div>;
  },
});

/**
 * A load button, which calls its onClick prop
 */
var ScheduleButton = React.createClass({
  propTypes: {
    onClick: React.PropTypes.func.isRequired,
  },

  render: function () {
    return <button onClick={this.props.onClick} className="reset-button">
      Open/Close
    </button>;
  },
});

/**
 * A refresh button, which calls its onClick prop
 */
var RefreshButton = React.createClass({
  propTypes: {
    onClick: React.PropTypes.func.isRequired,
  },

  render: function () {
    return <button onClick={this.props.onClick} className="refresh-button">
      Refresh
    </button>;
  },
});

/**
 * Calls its onClick prop to reset table greying/sorting
 */
var ResetButton = React.createClass({
  propTypes: {
    onClick: React.PropTypes.func.isRequired,
  },

  render: function () {
    return <button onClick={this.props.onClick} className="reset-button">
      Reset
    </button>;
  },
});

// Modified from react-json-table example code.
var SelectTable = React.createClass({
  
  propTypes: {
    rows: React.PropTypes.array.isRequired,
    saveState: React.PropTypes.shape({
      greyed: React.PropTypes.object.isRequired,
      sort: React.PropTypes.any.isRequired,
      reverse: React.PropTypes.bool.isRequired
    }).isRequired,
    header: React.PropTypes.bool.isRequired,
    columns: React.PropTypes.array,
    clickHeader: React.PropTypes.func.isRequired,
    clickRow: React.PropTypes.func.isRequired
  },
    
  getInitialState: function(){
    return {};
  },  
  render: function(){
    // clone the rows
    items = this.props.rows.slice();
    
    items = _.sortBy(items, this.props.saveState.sort);
    
    if (this.props.saveState.reverse) items.reverse();
    
    return <JsonTable 
      rows={items} 
      columns={this.props.columns}
      settings={ this.getSettings() } 
      onClickHeader={ this.onClickHeader }
      onClickRow={ this.onClickRow }
    />;
  },
  
  getSettings: function(){
      var me = this;
      // We will add some classes to the selected rows and cells
      return {
        headerClass: function( current, key ){
            if( me.props.saveState.sort == key ) {
              if ( me.props.saveState.reverse) {
                return current + ' headerSelected sortReversed';
              } else {
                return current + ' headerSelected';
              }
            } else {
              return current;
            }
        },
        rowClass: function( current, item ){
          if( me.props.saveState.greyed[item] ) {
            return current + ' rowGreyed';
          } else {
            return current;
          }
        },
        header: this.props.header
      };
  },
    
  onClickHeader: function( e, column ){
    this.props.clickHeader(column);
  },
  
  onClickRow: function( e, item ){ 
    this.props.clickRow(item);
  }
});
