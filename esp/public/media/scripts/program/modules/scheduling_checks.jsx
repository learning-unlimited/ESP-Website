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
    };
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

  render: function () {
    var body;
    if (this.state.failed) {
      body = <div className="placeholder">
        (loaded {this.state.timestamp}, loading failed ☹)
      </div>;
    } else if (!this.state.open) {
      body = <div className="placeholder">
        (loaded {this.state.timestamp}, click title to open)
      </div>;
    } else if (!this.state.data) {
      body = <div className="placeholder">loading...</div>;
    } else {
      var data = JSON.parse(this.state.data); // Might not work on old browsers
      var table;
      if (data.headings.length == 0) {
        var settings = {
          header: false
        };
        table = <SelectTable rows = {data.body} settings = {settings} />;
      } else {
        var columns = [];
        for (i = 0; i < data.headings.length; i++) {
          if (!!data.headings[i]) {
            columns[i] = {key: String(i), label: data.headings[i]};
          } else {
            columns[i] = {key: String(i), label: " "};
          }
        }
        table = <SelectTable rows = {data.body} columns = {columns} />;
      }
      body = <div>
        <div className="placeholder">
          (loaded {this.state.timestamp}, click title to close)
        </div>
        {table}
      </div>;
    }

    return <div className="scheduling-check">
      <div className="scheduling-check-title">
        <span onClick={this.handleClick}>{this.props.title}</span>
        <RefreshButton onClick={this.loadData} />
      </div>
      <div className="scheduling-check-body">
        {body}
      </div>
    </div>;
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
      ↻
    </button>;
  },
});


// Modified from react-json-table example code.
var SelectTable = React.createClass({
  getInitialState: function(){
    // We will store the sorted column and whether each row is greyed out
    var temp = new Array();
    for (i = 0; i < this.props.rows.length; i++) {
        temp[this.props.rows[i]] = false;
    }
    if (this.props.settings == undefined) {
        this.props.settings = {
          header: true
        };
    }
    return {sort: -1, greyed : temp};
  },  
  render: function(){
    var me = this,
        // clone the rows
        items = this.props.rows.slice()
    ;
    // Sort the table
    if( this.state.sort ){
      items.sort( function( a, b ){
         return a[ me.state.sort ] > b[ me.state.sort ] ? 1 : -1;
      });
    }
      
    if (this.props.columns == undefined) {
      return <JsonTable 
        rows={items} 
        settings={ this.getSettings() } 
        onClickHeader={ this.onClickHeader }
        onClickRow={ this.onClickRow }
      />;
    } else {
      return <JsonTable 
        rows={items} 
        columns={this.props.columns}
        settings={ this.getSettings() } 
        onClickHeader={ this.onClickHeader }
        onClickRow={ this.onClickRow }
      />;
    }
  },
  
  getSettings: function(){
      var me = this;
      // We will add some classes to the selected rows and cells
      return {
        headerClass: function( current, key ){
            if( me.state.sort == key )
              return current + ' headerSelected';
            return current;
        },
        rowClass: function( current, item ){
          if( me.state.greyed[item] )
            return current + ' rowGreyed';
          return current;
        },
        header: this.props.settings.header
      };
  },
    
  onClickHeader: function( e, column ){
    this.setState( {sort: column} );
  },
  
  onClickRow: function( e, item ){
    this.state.greyed[item] = !this.state.greyed[item];
    this.setState(); // so that it actually updates
  }
});
