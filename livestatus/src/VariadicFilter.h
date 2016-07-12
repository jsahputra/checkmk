// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef VariadicFilter_h
#define VariadicFilter_h

#include "config.h"  // IWYU pragma: keep
#include <deque>
#include <memory>
#include <string>
#include "Filter.h"
class FilterVisitor;
class Query;

enum class LogicalOperator { and_, or_ };

class VariadicFilter : public Filter {
public:
    typedef std::deque<Filter *> _subfilters_t;

    static std::unique_ptr<VariadicFilter> make(Query *query,
                                                LogicalOperator logicOp);
    virtual ~VariadicFilter();
    void accept(FilterVisitor &v) override;
    void addSubfilter(Filter *);
    Filter *stealLastSubfiler();
    void combineFilters(Query *query, int count, LogicalOperator andor);
    bool hasSubFilters() { return !_subfilters.empty(); }
    _subfilters_t::iterator begin() { return _subfilters.begin(); }
    _subfilters_t::iterator end() { return _subfilters.end(); }
    void findIntLimits(const std::string &colum_nname, int *lower,
                       int *upper) const override;

protected:
    explicit VariadicFilter(Query *query);
    _subfilters_t _subfilters;
};

#endif  // VariadicFilter_h
