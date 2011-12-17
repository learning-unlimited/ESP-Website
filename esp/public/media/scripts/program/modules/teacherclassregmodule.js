function check_grade_range(form, grade_min, grade_max)
{
    console.log("Checking!");
    if ($j(form).find('#id_grade_min').val() == grade_min && $j(form).find('#id_grade_max').val() == grade_max)
    {
        return confirm("Are you sure you want your class to have grade range 7-12? \
Managing a class with grade range 7-12 can be more difficult due to the \
difference in maturity levels between middle and high school students. \
Click OK if you are sure this is what you want, or click Cancel to go back \
and change the grade range.");
    }
    else
    {
        return true;
    }
}
