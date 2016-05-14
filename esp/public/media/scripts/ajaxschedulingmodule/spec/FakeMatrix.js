function generateFakeMatrix(){
    var sections = new Sections(section_fixture(),
                                 {},
                                 teacher_fixture(),
                                 schedule_assignment_fixture(),
                                 new ApiClient());
    var messagePanel = new MessagePanel($j("<div>"),
                                         "Welcome to the Ajax Scheduler!");
    var sectionInfoPanel = new SectionInfoPanel($j("<div>"),
                                                 sections,
                                                 messagePanel)
    var matrix = new Matrix(new Timeslots(time_fixture()),
                  room_fixture(),
                  sections,
                  $j("<div>"),
                  messagePanel,
                  sectionInfoPanel);
    matrix.getTable = function() {
        return this.el.find(".ft_scroller table")[0];
    }
    matrix.render();
    return matrix;

}
